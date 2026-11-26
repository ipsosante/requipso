"""Core block classes for the pipes module.

This module defines the block hierarchy:
- BaseBlock: Abstract base defining the pipeline interface (execute/run)
- TableBlock: For blocks that transform raw database tables (patient or event level)
- CombinedBlock: For combining multiple boolean blocks with AND/OR logic
- Negation: Complement of another step with respect to its parent
"""

import datetime
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, TypeVar, cast

import polars as pl
from sqlglot import exp, parse_one

from requipso.data import Data

from .params import BlockParams

ParamsT = TypeVar("ParamsT", bound=BlockParams)


def sql_to_polars_expr(col: pl.Expr, sql: str) -> pl.Expr:
    expression = parse_one(
        sql.replace('"', "'")
    )  # Use single quote since double quotes are used for column references

    def rename_column(node):
        if isinstance(node, exp.Column) and node.name == "x":
            return exp.column(col.meta.output_name())
        return node

    new_expression = expression.transform(rename_column)
    expr: pl.Expr = pl.sql_expr(new_expression.sql())
    return expr


# =============================================================================
# Output Types
# =============================================================================


class OutputType(Enum):
    """Output type enum for block results."""

    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"
    CATEGORY = "category"


# =============================================================================
# Block Configuration
# =============================================================================


@dataclass
class BlockConfig:
    """Configuration for a TableBlock."""

    output_type: OutputType
    block_type: Literal["patient", "event"] = "event"

    # Date handling: either single date (e.g. for a single event) or a date range (start_date, end_date)
    # Or None if the block doesn't involve dates
    date_column: str | tuple[str, str] | None = None
    description: str | None = None


# =============================================================================
# BaseBlock - Pipeline Interface
# =============================================================================


class BaseBlock(ABC):
    """Abstract base for all blocks. Defines the pipeline interface.

    All blocks (TableBlock subclasses and CombinedBlock) share this interface,
    making them fully interchangeable in pipelines.
    """

    def __init__(self, name: str | None = None):
        self.name = name or self.__class__.__name__
        self.has_date: bool = False

    @abstractmethod
    def execute(
        self,
        data: Data,
        reference_date: datetime.datetime | pl.DataFrame | None = None,
        patient_ids: pl.Series | None = None,
    ) -> Data:
        """Execute the block and return DataFrame with patient_id + self.name columns."""
        ...


# =============================================================================
# TableBlock - For Table-Based Transformations
# =============================================================================


class TableBlock(BaseBlock, Generic[ParamsT]):
    """Base for blocks that transform raw database tables.

    Extends BaseBlock with:
    - BlockConfig for table/output_type/date_column configuration
    - transform() method for the core transformation logic
    - Date filtering capabilities
    - Aggregation and post-transform function support

    Generic over P (bound to BlockParams) so subclasses can narrow the params type:
        class MyBlock(TableBlock[MyParams]):
            ...
    """

    config: BlockConfig  # Declared by subclasses
    params: ParamsT  # Parameters for the block

    def __init__(self, name: str | None = None, params: ParamsT | None = None):
        super().__init__(name=name)
        self.params = params if params is not None else self.params
        self.reference_date: pl.DataFrame | None = None
        self.start_date_column: str | None = None
        self.end_date_column: str | None = None

        if self.config.date_column is not None:
            self.has_date = True
            if isinstance(self.config.date_column, str):
                self.start_date_column = self.config.date_column
                self.end_date_column = self.config.date_column
            else:
                self.start_date_column, self.end_date_column = self.config.date_column

    @property
    def output_type(self) -> OutputType:
        return self.config.output_type

    def get_tables(
        self,
        data: Data,
        table_names: list[str],
        patient_ids: pl.Series | None = None,
    ) -> dict[str, pl.DataFrame]:
        tables = {name: data.get_table(name) for name in table_names}
        if patient_ids is not None:
            tables = {
                name: df.filter(pl.col("patient_id").is_in(patient_ids))
                if "patient_id" in df.columns
                else df
                for name, df in tables.items()
            }
        return tables

    def filter_date(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """Apply date filter to the given DataFrame."""
        if self.reference_date is None:
            return df

        df = df.join(self.reference_date, on="patient_id", how="left")

        if self.params.date_sql:
            assert self.has_date, "Date SQL cannot be applied without date information"
            # Here we know that the date column is either start_date or end_date
            date_col = "end_date" if "end_date" in df.columns else "start_date"
            # check if we have TZ informations
            tz = getattr(df[date_col].dtype, "time_zone", None)
            if tz is not None:
                df = df.with_columns(
                    reference_date=pl.col("reference_date").dt.replace_time_zone(tz)
                )
            return df.filter(pl.sql_expr(self.params.date_sql))
        else:
            return df

    @abstractmethod
    def transform(self, **tables: pl.DataFrame) -> pl.DataFrame:
        """Core transformation. Returns DataFrame with patient_id + self.name columns."""
        ...

    def set_reference_date(
        self,
        data: Data,
        reference_date: datetime.datetime | pl.DataFrame | None = None,
    ) -> None:
        """Resolve reference date from params if a reference_date_block is set.

        If ``self.params.reference_date_block`` is set, fetches per-patient reference
        dates from the block's results. Otherwise, falls back to the
        *reference_date* argument passed by the caller (typically the
        pipeline-level default).
        """

        # Reference date from other step
        ref_block = self.params.reference_date_block if self.params else None
        if ref_block is not None:
            print(f"Using reference date from block {ref_block.name}")

            reference_date_sql = self.params.reference_date_sql

            if reference_date_sql is None:
                # Default: use first start_date
                reference_date_sql = "MIN(start_date)"

            self.reference_date = (
                data.all_results[ref_block.name]["dates"]
                .group_by("patient_id")
                .agg(pl.sql_expr(reference_date_sql).alias("reference_date"))
            )

            return

        # Single reference date from argument
        if isinstance(reference_date, datetime.datetime):
            self.reference_date = data.patient.select(
                "patient_id",
                pl.lit(reference_date).alias("reference_date"),
            )
        elif isinstance(reference_date, pl.DataFrame):
            # Join reference dates to df and apply filter
            if (
                "patient_id" not in reference_date.columns
                or "reference_date" not in reference_date.columns
            ):
                raise ValueError(
                    "reference_date DataFrame must contain 'patient_id' and 'reference_date' columns"
                )
            if (
                reference_date.get_column("patient_id").n_unique()
                != reference_date.height
            ):
                raise ValueError(
                    "reference_date DataFrame must have one row per patient_id"
                )
            self.reference_date = reference_date.select("patient_id", "reference_date")

    def execute(
        self,
        data: Data,
        reference_date: datetime.datetime | pl.DataFrame | None = None,
        patient_ids: pl.Series | None = None,
    ) -> Data:

        n = patient_ids.len() if patient_ids is not None else "all"
        print(f"Executing block {self.name} on {n} patients")

        table_names = list(
            set(inspect.signature(inspect.unwrap(self.transform)).parameters.keys())
        )
        tables = self.get_tables(data, table_names=table_names, patient_ids=patient_ids)
        self.set_reference_date(data, reference_date)

        df = self.transform(**tables)
        if self.start_date_column is not None:
            df = df.with_columns(
                start_date=pl.col(self.start_date_column),
            )
        if self.end_date_column is not None:
            df = df.with_columns(
                end_date=pl.col(self.end_date_column).fill_null(
                    datetime.datetime.now().date()
                ),  # If no end date, assume still active
            )

        if self.has_date:
            df = self.filter_date(df)
            # Sort by patient_id and date (useful for certain post-transforms like LAST)
            df = df.sort(["patient_id", self.start_date_column])

            data.all_results[self.name]["dates"] = df.select(
                "patient_id",
                self.name,
                pl.col("start_date").dt.date().alias("start_date"),
                pl.col("end_date").dt.date().alias("end_date"),
            )

        # Aggregate to patient level
        agg = self.params.agg_func

        if agg:
            # print(f"Applying aggregation for block {self.name}: {agg}")
            aggs = [agg(pl.col(self.name)).alias(self.name)]
            df = df.group_by("patient_id").agg(*aggs)

        # Adding all patients back
        all_patients = (
            patient_ids.to_frame(name="patient_id")
            if patient_ids is not None
            else data.patient.select("patient_id")
        )
        df = all_patients.join(df, on="patient_id", how="left")

        # Post-transform
        post = self.params.post_func
        if post:
            # print(f"Applying post-transform for block {self.name}: {post}")
            df = df.with_columns(post(pl.col(self.name)).alias(self.name))

        data.all_results[self.name]["post"] = df

        print(self.name, df.group_by(self.name).len())

        return data


# =============================================================================
# CombinedBlock - Combine Multiple Blocks
# =============================================================================


class CombinedBlock(BaseBlock):
    """Combines multiple boolean blocks with AND/OR logic.

    Extends BaseBlock directly (not TableBlock) because it doesn't work on raw
    tables - it composes other block outputs.

    Can contain any BaseBlock, including other CombinedBlock instances,
    enabling nested compositions.
    """

    output_type = OutputType.BOOLEAN

    def __init__(
        self,
        blocks: list[BaseBlock],
        operator: Literal["AND", "OR"] | list[Literal["AND", "OR"]] = "AND",
        name: str | None = None,
        store_intermediate_results: bool = True,
        expose_date_for_future_references: list[bool] | None = None,
    ):
        """
        expose_date_for_future_references: list[bool] | None = None,
        If True, the date from the block will be available for reference_date of subsequent blocks.
        If False, the date from the block will not be exposed
        """
        if isinstance(operator, str):
            operator = [operator] * (len(blocks) - 1)

        if len(operator) != len(blocks) - 1:
            raise ValueError(
                f"operator list must have length len(blocks) - 1 "
                f"({len(blocks) - 1}), got {len(operator)}"
            )

        auto_name = (
            "("
            + "".join(f"_{b.name}{op}" for b, op in zip(blocks, operator))
            + f"_{blocks[-1].name})"
        )
        super().__init__(name=name or auto_name)
        self.blocks = blocks
        self.operator = operator
        self.store_intermediate_results = store_intermediate_results

        if expose_date_for_future_references is not None:
            if len(expose_date_for_future_references) != len(blocks):
                raise ValueError(
                    "expose_date_for_future_references must be the same length as blocks"
                )
            self.expose_date_for_future_references = expose_date_for_future_references
        else:
            self.expose_date_for_future_references = [True] * len(blocks)

    def execute(
        self,
        data: Data,
        reference_date: datetime.datetime | pl.DataFrame | None = None,
        patient_ids: pl.Series | None = None,
    ) -> Data:
        combined = data.patient.select("patient_id")
        data.all_results[self.name]["dates"] = []  # will be combined at the end

        for block, expose_date in zip(
            self.blocks, self.expose_date_for_future_references
        ):
            block.execute(data, reference_date=reference_date, patient_ids=patient_ids)

            tmp = data.all_results[block.name]["post"].select("patient_id", block.name)
            combined = combined.join(tmp, on="patient_id", how="left")

            if expose_date and block.has_date:
                # If at least one block has_date, the self has_date
                self.has_date = True
                # Filter the dates to only include the patients that passed the step
                output_patients = (
                    data.all_results[block.name]["post"]
                    .filter(pl.col(block.name))
                    .get_column("patient_id")
                    .unique()
                )

                # Filter the dates to only include the patients that passed the step
                data.all_results[block.name]["dates"] = data.all_results[block.name][
                    "dates"
                ].filter(pl.col("patient_id").is_in(output_patients))

                data.all_results[self.name]["dates"].append(
                    data.all_results[block.name]["dates"].select(
                        "patient_id",
                        pl.col(block.name).alias(self.name),
                        pl.col("start_date").dt.date().alias("start_date"),
                        pl.col("end_date").dt.date().alias("end_date"),
                    )
                )

        if self.has_date:
            data.all_results[self.name]["dates"] = pl.concat(
                data.all_results[self.name]["dates"]
            )

        # Combine with operators sequentially
        cols = [pl.col(b.name).fill_null(False) for b in self.blocks]
        expr = cols[0]
        for op, c in zip(self.operator, cols[1:]):
            if op == "OR":
                expr = expr | c
            else:
                expr = expr & c

        columns = ["patient_id", expr.alias(self.name)]
        if self.store_intermediate_results:
            columns += [pl.col(b.name) for b in self.blocks]

        data.all_results[self.name]["post"] = combined.select(columns)

        return data


# =============================================================================
# Negation - Complement of Another Step
# =============================================================================


class Negation(BaseBlock):
    """Patients of the target step's parent that the target step did not keep.

    Placed in the pipeline as a sibling of ``target`` (same parent), so the
    ``patient_ids`` it receives are the target's own input patients. Those are
    used as the universe rather than ``target``'s ``post`` table, because a
    ``CombinedBlock`` stores ``False`` for every patient of the database.
    """

    output_type = OutputType.BOOLEAN
    description = (
        "Complément d'une étape : patients de l'étape parente non retenus par "
        "l'étape indiquée dans value. Permet de créer la branche « sinon »."
    )
    value_help = (
        "[HELP] block_name de l'étape à inverser (définie plus haut, pas la "
        "première étape). Laisser parent_step vide."
    )

    def __init__(self, target: BaseBlock, name: str | None = None):
        super().__init__(name=name or f"NOT_{target.name}")
        self.target = target

    def execute(
        self,
        data: Data,
        reference_date: datetime.datetime | pl.DataFrame | None = None,
        patient_ids: pl.Series | None = None,
    ) -> Data:
        if "post" not in data.all_results[self.target.name]:
            raise ValueError(
                f"Step {self.name}: step {self.target.name!r} must be executed first"
            )

        inputs = (
            patient_ids.to_frame(name="patient_id")
            if patient_ids is not None
            else data.patient.select("patient_id")
        )
        target = data.all_results[self.target.name]["post"].select(
            "patient_id", self.target.name
        )
        data.all_results[self.name]["post"] = inputs.join(
            target, on="patient_id", how="left"
        ).select(
            "patient_id",
            (~pl.col(self.target.name).fill_null(False)).alias(self.name),
        )

        return data
