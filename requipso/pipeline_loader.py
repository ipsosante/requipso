"""Pipeline loader: build a Pipeline from a Google Sheets definition.

Uses ``gspread-pandas`` to read worksheets directly as pandas DataFrames,
providing cleaner column access and simpler row handling compared to the
raw ``gspread`` approach.

Usage::

    from requipso.pipeline_loader import PipelineBuilder

    builder = PipelineBuilder()
    pipeline = builder.build()
    data = pipeline.run(data)
"""

from __future__ import annotations

import ast
import datetime
import importlib
import inspect
import json
import logging
import pkgutil
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal, cast, get_args, get_origin

import pandas as pd
from gspread_pandas import Spread  # type: ignore

from requipso.data import Data
from requipso.descriptive_pipeline import VARIABLE_TYPE, DescriptivePipeline
from requipso.google import GoogleConnector
from requipso.pipeline import Pipeline
from requipso.pipes.base import (
    BaseBlock,
    CombinedBlock,
    TableBlock,
)
from requipso.pipes.params import BlockParams

logger = logging.getLogger(__name__)

SHEET_ID = "1a3pZ-9AIQrzN26cxjlrIdR7BdNN2KB-ZHwI74dEKSRI"
PIPELINE_SHEET_NAME = "Inclusion"
DESCRIPTIVE_PIPELINE_SHEET_NAME = "Descriptive_table"
PROJECT_SHEET_NAME = "Project"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

COMMON_PARAM_COLUMNS = [
    "value",
    "agg_func",
    "post_func",
    "reference_date_block",
    "reference_date_sql",
    "date_sql",
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class RowGroup:
    """A group of consecutive sheet rows that define a single pipeline step."""

    name: str
    rows: list[pd.Series]
    parent_step: str
    text: str
    excluded_text: str
    operator: list[Literal["AND", "OR"]]
    expose_date_for_future_references: list[bool]


@dataclass
class DescriptiveRowGroup:
    """A group of consecutive sheet rows that define a descriptive-pipeline row."""

    name: str
    rows: list[pd.Series]
    operator: list[Literal["AND", "OR"]]
    description: str | None
    subsets: list[Any] | None
    variable_type: VARIABLE_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_supplementary_params(raw: Any) -> dict[str, Any]:
    """Lenient JSON parsing for the ``supplementary_params`` column.

    Tries, in order: ``json.loads``, quote-normalisation + unquoted-key fix,
    ``ast.literal_eval``.  Returns ``{}`` on total failure.
    """
    if raw is None or pd.isna(raw):
        return {}
    raw = str(raw).strip()
    if not raw:
        return {}

    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    normalized = raw.replace("'", '"')
    normalized = re.sub(r'([{,])\s*(\w+)"\s*:', r'\1"\2":', normalized)
    normalized = re.sub(r"([{,])\s*(\w+)\s*:", r'\1"\2":', normalized)
    try:
        result = json.loads(normalized)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    logger.warning("Could not parse supplementary_params: %r", raw)
    return {}


def parse_subsets(raw: Any) -> list[Any] | None:
    """Lenient parsing for the ``subsets`` column (expected to be a list literal)."""
    if raw is None or pd.isna(raw):
        return None
    text = str(raw).strip()
    if not text:
        return None

    for parser in (
        json.loads,
        lambda s: json.loads(s.replace("'", '"')),
        ast.literal_eval,
    ):
        try:
            result = parser(text)
        except (json.JSONDecodeError, ValueError, SyntaxError):
            continue
        if isinstance(result, list):
            return result

    logger.warning("Could not parse subsets: %r", raw)
    return None


def extract_params_type(block_cls: type) -> type[BlockParams] | None:
    """Read the generic ``Params`` arg from ``TableBlock[P]``."""
    for base in getattr(block_cls, "__orig_bases__", ()):
        origin = get_origin(base)
        if origin is TableBlock:
            args = get_args(base)
            if args and inspect.isclass(args[0]):
                return args[0]
    return None


def build_block_registry() -> dict[str, type[TableBlock]]:
    """Walk ``requipso.pipes`` and return ``{class_name: class}``."""
    pkg = importlib.import_module("requipso.pipes")
    modules: list[Any] = [pkg]
    if hasattr(pkg, "__path__"):
        for info in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg.__name__}."):
            try:
                modules.append(importlib.import_module(info.name))
            except Exception:  # noqa: BLE001
                continue

    registry: dict[str, type[TableBlock]] = {}
    for mod in modules:
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                obj not in (TableBlock, BaseBlock)
                and issubclass(obj, TableBlock)
                and obj.__module__.startswith("requipso.pipes")
            ):
                registry[obj.__name__] = obj
    return registry


def _check_required_columns(
    df: pd.DataFrame, required: list[str], context: str
) -> None:
    missing = [c for c in required if c not in df]
    if missing:
        raise ValueError(f"Missing required {context} columns: {missing}")


def _iter_block_groups(
    df: pd.DataFrame,
) -> Iterator[tuple[str, list[pd.Series]]]:
    """Yield ``(block_name, rows)`` for each consecutive group of rows.

    Rows are grouped by ``block_name`` continuity: a non-empty ``block_name``
    that differs from the previous one starts a new group; rows without a
    ``block_name`` (or repeating it) are appended to the current group.
    """
    current_name: str | None = None
    current_rows: list[pd.Series] = []
    for _, row in df.iterrows():
        block_name = row.block_name
        if block_name and block_name != current_name:
            if current_rows and current_name is not None:
                yield current_name, current_rows
            current_name = block_name
            current_rows = [row]
        elif current_name is not None:
            current_rows.append(row)
    if current_rows and current_name is not None:
        yield current_name, current_rows


def _extract_operators(
    rows: list[pd.Series], block_name: str
) -> list[Literal["AND", "OR"]]:
    """Validate and collect ``operator`` values from continuation rows."""
    operators: list[Literal["AND", "OR"]] = []
    for row in rows[1:]:
        op = row.operator
        if op not in ("AND", "OR"):
            raise ValueError(f"Invalid operator {op!r} in block {block_name!r}")
        operators.append(cast(Literal["AND", "OR"], op))
    return operators


def parse_row_groups(df: pd.DataFrame) -> list[RowGroup]:
    """Group consecutive DataFrame rows by ``block_name`` continuity."""
    _check_required_columns(
        df,
        required=[
            "block_name",
            "parent_step",
            "operator",
            "text",
            "excluded_text",
            "block_type",
            "expose_date_for_future_references",
        ],
        context="pipeline",
    )

    groups: list[RowGroup] = []
    for name, rows in _iter_block_groups(df):
        first = rows[0]
        operators = _extract_operators(rows, name)

        expose_dates: list[bool] = [first.expose_date_for_future_references]
        for row in rows[1:]:
            val = row.expose_date_for_future_references
            if not isinstance(val, bool):
                raise ValueError(
                    f"Invalid expose_date_for_future_references {val!r} in block {name!r}"
                )
            expose_dates.append(val)

        groups.append(
            RowGroup(
                name=name,
                rows=rows,
                parent_step=first.parent_step,
                text=first.text,
                excluded_text=first.excluded_text,
                operator=operators,
                expose_date_for_future_references=expose_dates,
            )
        )

    return groups


def parse_descriptive_row_groups(df: pd.DataFrame) -> list[DescriptiveRowGroup]:
    """Group consecutive DataFrame rows from the Descriptive sheet."""
    _check_required_columns(
        df,
        required=["block_name", "operator", "block_type", "variable_type"],
        context="descriptive",
    )

    allowed_types = get_args(VARIABLE_TYPE)
    groups: list[DescriptiveRowGroup] = []
    for name, rows in _iter_block_groups(df):
        first = rows[0]
        operators = _extract_operators(rows, name)

        variable_type = first.variable_type
        if variable_type not in allowed_types:
            raise ValueError(
                f"Invalid variable_type {variable_type!r} in block {name!r}; "
                f"expected one of {allowed_types}"
            )

        description = first.get("variable_description")
        if description is not None and pd.isna(description):
            description = None

        groups.append(
            DescriptiveRowGroup(
                name=name,
                rows=rows,
                operator=operators,
                description=description,
                subsets=parse_subsets(first.get("subsets")),
                variable_type=cast(VARIABLE_TYPE, variable_type),
            )
        )

    return groups


# ---------------------------------------------------------------------------
# PipelineBuilder
# ---------------------------------------------------------------------------


class PipelineBuilder:
    """Build a :class:`~requipso.pipeline.Pipeline` from a Google Sheet.

    Uses ``gspread-pandas`` to read worksheets as pandas DataFrames.

    Parameters
    ----------
    spreadsheet_key : str
        The spreadsheet ID (from the Google Sheets URL).
    sheet_name : str
        Name of the worksheet containing the pipeline definition.
    credentials_path : Path
        Path to a service-account JSON key file.
    """

    def __init__(
        self,
        google_connector: GoogleConnector,
    ) -> None:
        self.google_connector = google_connector

        if self.google_connector.spreadsheet_name is None:
            raise ValueError("Spreadsheet name not set")

        self.spreadsheet_key = self.google_connector.spreadsheet_key
        self.spreadsheet_name = self.google_connector.spreadsheet_name

        self.registry = build_block_registry()
        self.spread = cast(Spread, self.google_connector.spread)

        self.pipeline_hash = None
        # to set hash
        self.fetch_pipeline_df()

    # -- sheet access -------------------------------------------------------

    def fetch_pipeline_df(self) -> pd.DataFrame:
        """Read the pipeline definition worksheet as a DataFrame."""
        df = self.google_connector.open_sheet(PIPELINE_SHEET_NAME).dropna(
            subset="block_type"
        )
        self.pipeline_hash = pd.util.hash_pandas_object(df).sum()
        return df

    def fetch_reference_date(self) -> datetime.datetime:
        """Read the global reference date from cell B1 of the Project sheet."""
        df = self.google_connector.open_sheet(PROJECT_SHEET_NAME, header_rows=0)
        if df.empty or df.shape[1] < 2:
            raise ValueError(
                f"Reference date not found in {PROJECT_SHEET_NAME!r} cell B1"
            )
        raw = df.iloc[0, 1]
        if pd.isna(raw):
            raise ValueError(
                f"Reference date not found in {PROJECT_SHEET_NAME!r} cell B1"
            )
        return datetime.datetime.strptime(str(raw), "%d/%m/%Y")

    def fetch_populations(self) -> list[str]:
        """Read population names from row 2 of the Project sheet.

        A2 must be the label ``"Populations"``; B2, C2, … contain one
        population name per cell.
        """
        df = self.google_connector.open_sheet(PROJECT_SHEET_NAME, header_rows=0)
        if df.shape[0] < 2 or df.shape[1] < 2:
            raise ValueError(
                f"Populations row not found in {PROJECT_SHEET_NAME!r} row 2"
            )

        label = df.iloc[1, 0]
        if pd.isna(label) or str(label).strip() != "Populations":
            raise ValueError(
                f"Expected cell A2 of {PROJECT_SHEET_NAME!r} to be 'Populations', "
                f"got {label!r}"
            )

        populations = [
            str(val).strip()
            for val in df.iloc[1, 1:]
            if not pd.isna(val) and str(val).strip()
        ]
        if not populations:
            raise ValueError(
                f"No populations found in {PROJECT_SHEET_NAME!r} row 2 "
                f"(expected at least one value in B2, C2, …)"
            )
        return populations

    # -- block instantiation ------------------------------------------------

    def build_block_from_row(
        self,
        row: pd.Series,
        name: str,
        built_blocks: dict[str, BaseBlock],
    ) -> BaseBlock:
        """Instantiate a single block from one sheet row."""
        block_type_name = row.block_type
        block_cls = self.registry.get(block_type_name)
        if block_cls is None:
            raise ValueError(
                f"Unknown block type: {block_type_name!r}. "
                f"Available: {sorted(self.registry)}"
            )

        params_cls = extract_params_type(block_cls)
        if params_cls is None:
            return block_cls(name=name)

        params_dict: dict[str, Any] = {}
        for col in COMMON_PARAM_COLUMNS:
            raw = row.get(col)
            if pd.isna(raw):
                continue
            if col == "reference_date_block":
                ref_block = built_blocks.get(raw)
                if ref_block is None:
                    raise ValueError(
                        f"reference_date_block {raw!r} not found — "
                        f"it must appear earlier in the sheet."
                    )
                params_dict["reference_date_block"] = ref_block
            else:
                params_dict[col] = raw

        supp_raw = row.get("supplementary_params")
        supp = parse_supplementary_params(supp_raw)
        params_dict.update(supp)

        params = params_cls(**params_dict)
        return block_cls(name=name, params=params)

    def build_block_for_group(
        self,
        group: RowGroup | DescriptiveRowGroup,
        built_blocks: dict[str, BaseBlock],
        *,
        expose_date_for_future_references: list[bool] | None = None,
    ) -> BaseBlock:
        """Build a single :class:`BaseBlock` (possibly :class:`CombinedBlock`) from a row group."""
        if len(group.rows) == 1:
            return self.build_block_from_row(group.rows[0], group.name, built_blocks)

        sub_blocks: list[BaseBlock] = []
        for i, row in enumerate(group.rows):
            sub_name = f"{group.name}_{i}"
            sub_blocks.append(self.build_block_from_row(row, sub_name, built_blocks))

        return CombinedBlock(
            blocks=sub_blocks,
            operator=group.operator,
            name=group.name,
            expose_date_for_future_references=expose_date_for_future_references,
        )

    # -- public API ---------------------------------------------------------

    def parse(self) -> list[RowGroup]:
        df = self.fetch_pipeline_df()
        if df.empty:
            raise ValueError("Sheet is empty")

        groups = parse_row_groups(df)
        return groups

    def build(self) -> Pipeline:
        """Fetch the sheet and construct a :class:`Pipeline`."""
        groups = self.parse()
        reference_date = self.fetch_reference_date()
        logger.info("Reference date: %s", reference_date)
        pipeline = Pipeline(reference_date=reference_date)
        built_blocks: dict[str, BaseBlock] = {}

        for group in groups:
            block = self.build_block_for_group(
                group,
                built_blocks,
                expose_date_for_future_references=group.expose_date_for_future_references,
            )
            built_blocks[group.name] = block
            pipeline.add_step(
                block,
                text=group.text,
                excluded_text=group.excluded_text,
                parent_step=group.parent_step,
            )

        return pipeline

    def build_descriptive(
        self,
        data: Data,
        inclusion_pipeline: Pipeline,
        sheet_name: str = DESCRIPTIVE_PIPELINE_SHEET_NAME,
    ) -> DescriptivePipeline:
        """Fetch the descriptive sheet and construct a :class:`DescriptivePipeline`.

        Parameters
        ----------
        data : Data
            The dataset on which the *inclusion_pipeline* has already been run.
        inclusion_pipeline : Pipeline
            A :class:`Pipeline` whose steps already exist in ``data.all_results``;
            its ``steps_names`` are also exposed for ``reference_date_block`` lookups.
        sheet_name : str
            Name of the worksheet that defines the descriptive rows
            (defaults to :data:`DESCRIPTIVE_PIPELINE_SHEET_NAME`).
        """

        populations = self.fetch_populations()
        logger.info("Populations: %s", populations)

        df = self.google_connector.open_sheet(sheet_name).dropna(subset="block_type")
        if df.empty:
            raise ValueError(f"Descriptive sheet {sheet_name!r} is empty")

        groups = parse_descriptive_row_groups(df)

        descriptive = DescriptivePipeline(
            data=data,
            inclusion_pipeline=inclusion_pipeline,
            populations=populations,
            google_connector=self.google_connector,
        )

        # Seed with inclusion-pipeline blocks so descriptive rows can reference
        # them via ``reference_date_block`` without having to redeclare them.
        built_blocks: dict[str, BaseBlock] = dict(inclusion_pipeline.steps_names)

        for group in groups:
            block = self.build_block_for_group(group, built_blocks)
            built_blocks[group.name] = block
            descriptive.add_row(
                step=block,
                variable_type=group.variable_type,
                display_name=group.description,
                subsets=group.subsets,
            )

        return descriptive
