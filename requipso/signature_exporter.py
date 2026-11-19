"""Export block signatures for ``TableBlock`` subclasses.

Discovers every concrete block under ``requipso.pipes`` at runtime using
:mod:`inspect` and :func:`typing.get_args`, then extracts:

* the generic ``Params`` type (e.g. ``DepartementParams``)
* the ``BlockConfig.description`` and ``BlockConfig.block_type``
* common vs. block-specific parameter metadata (type + default)

Usage::

    # From the CLI
    python scripts/signature_exporter.py
    python scripts/signature_exporter.py --json --output-dir out/

    # As an importable API
    from requipso.signature_exporter import BlockExporter
    exporter = BlockExporter()
    exporter.to_csv(Path("out"))
    print(exporter.to_json())
"""

from __future__ import annotations

import argparse
import csv
import importlib
import inspect
import json
import pkgutil
import types
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from requipso.pipes.base import TableBlock
from requipso.pipes.params import BlockParams

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
SHEET_ID = "1IP81iXH-jK7HiZOCYBwOBvKM-4gxZ4KreagovULd-KM"


@dataclass(frozen=True)
class BlockSignature:
    """Introspected metadata for a single block class."""

    module: str
    block_name: str
    block_type: str  # "patient" or "event"
    params_name: str | None
    params_module: str | None
    description: str | None
    common_parameters: dict[str, dict[str, Any]]
    specific_parameters: dict[str, dict[str, Any]]
    has_date: bool


# ---------------------------------------------------------------------------
# Type / field helpers (stateless utilities)
# ---------------------------------------------------------------------------


def _type_to_string(annotation: Any) -> str:
    """Render a type annotation as a human-readable string.

    ``str | None`` becomes ``"str"`` (None is stripped from unions).
    """
    if annotation is None or annotation is type(None):
        return "None"
    if isinstance(annotation, str):
        return annotation

    origin = get_origin(annotation)

    # Handle Union / X | Y — drop NoneType, simplify single-member unions
    if origin is Union or isinstance(annotation, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _type_to_string(args[0])
        return " | ".join(_type_to_string(a) for a in args)

    if origin is not None:
        args = get_args(annotation)  # type: ignore
        origin_name = getattr(origin, "__name__", repr(origin).replace("typing.", ""))
        if not args:
            return origin_name
        return f"{origin_name}[{', '.join(_type_to_string(a) for a in args)}]"

    return getattr(annotation, "__name__", repr(annotation).replace("typing.", ""))


def _normalize_default(value: Any) -> Any:
    """Convert a default value to a JSON-serializable form."""
    if value is inspect._empty:
        return None
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def _model_fields(model_t: type[BaseModel]) -> dict[str, dict[str, Any]]:
    """Return ``{field_name: {"type": ..., "default": ..., "description": ...}}`` for a Pydantic model."""
    return {
        name: {
            "type": _type_to_string(field.annotation),
            "default": (field.description or "")
            if name == "value"
            else (None if field.is_required() else _normalize_default(field.default)),
            "description": field.description or "",
        }
        for name, field in model_t.model_fields.items()
    }


def _split_params_fields(
    params_t: type[Any] | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Separate common (``BlockParams``) fields from block-specific ones.

    Common keys are defined by ``BlockParams``, but type and default come
    from *params_t* so per-block overrides (e.g. ``agg_func``) are preserved.
    """
    base_common = _model_fields(BlockParams)
    if params_t is None or not issubclass(params_t, BaseModel):
        return base_common, {}

    all_fields = _model_fields(params_t)
    common: dict[str, dict[str, Any]] = {}
    for name in base_common:
        field = all_fields.get(name, base_common[name])
        # Inherit description from BlockParams when the subclass override lacks one
        if not field.get("description") and base_common[name].get("description"):
            field = {**field, "description": base_common[name]["description"]}
        common[name] = field
    specific = {n: s for n, s in all_fields.items() if n not in base_common}
    return common, specific


# ---------------------------------------------------------------------------
# BlockExporter
# ---------------------------------------------------------------------------


class BlockExporter:
    """Discover ``TableBlock`` subclasses and export their signatures.

    Discovery runs once at construction; the resulting :pyattr:`signatures` list
    is then available for export via :meth:`to_json`, :meth:`to_csv`, or direct
    iteration.

    Example::

        exporter = BlockExporter()
        for sig in exporter.signatures:
            print(sig.block_name, sig.params_name)
        exporter.to_csv(Path("out"))
    """

    def __init__(self) -> None:
        self.signatures: list[BlockSignature] = self._collect()

    # -- discovery ----------------------------------------------------------

    @staticmethod
    def _iter_pipes_modules() -> list[Any]:
        """Import every module under ``requipso.pipes``."""
        pkg = importlib.import_module("requipso.pipes")
        modules: list[Any] = [pkg]
        if not hasattr(pkg, "__path__"):
            return modules

        for info in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg.__name__}."):
            try:
                modules.append(importlib.import_module(info.name))
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] Could not import {info.name}: {exc}")

        return modules

    @staticmethod
    def _extract_params_type(block_cls: type[Any]) -> type[Any] | None:
        """Read the generic ``Params`` arg from ``TableBlock[P]``."""
        for base in getattr(block_cls, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is TableBlock:
                args = get_args(base)
                if args and inspect.isclass(args[0]):
                    return args[0]
        return None

    @staticmethod
    def _is_block_subclass(obj: Any) -> bool:
        """Return *True* for concrete block classes defined inside ``requipso.pipes``."""
        return (
            inspect.isclass(obj)
            and obj is not TableBlock
            and issubclass(obj, TableBlock)
            and obj.__module__.startswith("requipso.pipes")
        )

    def _collect(self) -> list[BlockSignature]:
        """Walk ``requipso.pipes`` and build a sorted list of :class:`BlockSignature`."""
        signatures: list[BlockSignature] = []

        for module in self._iter_pipes_modules():
            for _, obj in inspect.getmembers(module, self._is_block_subclass):
                params_t = self._extract_params_type(obj)
                config = getattr(obj, "config", None)
                block_type = getattr(config, "block_type", "event")
                has_date = getattr(config, "date_column", None) is not None
                common, specific = _split_params_fields(params_t)
                description = getattr(config, "description", None)

                signatures.append(
                    BlockSignature(
                        module=obj.__module__,
                        block_name=obj.__name__,
                        block_type=block_type,
                        has_date=has_date,
                        params_name=params_t.__name__ if params_t else None,
                        params_module=params_t.__module__ if params_t else None,
                        description=description,
                        common_parameters=common,
                        specific_parameters=specific,
                    )
                )

        signatures.sort(key=lambda s: (s.module, s.block_name))
        return signatures

    # -- export: JSON -------------------------------------------------------

    def to_json(self, **kwargs: Any) -> str:
        """Serialize all signatures to a JSON string.

        Extra *kwargs* are forwarded to :func:`json.dumps`.
        """
        kwargs.setdefault("indent", 2)
        kwargs.setdefault("ensure_ascii", False)
        return json.dumps([asdict(s) for s in self.signatures], **kwargs)

    # -- export: CSV --------------------------------------------------------

    @property
    def _common_parameter_names(self) -> list[str]:
        """Common parameter names in ``BlockParams`` definition order."""
        return list(BlockParams.model_fields.keys())

    def to_csv(self, output_dir: Path) -> tuple[Path, Path]:
        """Write both CSV files and return their paths.

        Returns
        -------
        (common_csv, specific_csv)
            Paths to the generated files.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        common_csv = self._write_common_csv(output_dir)
        specific_csv = self._write_specific_csv(output_dir)
        return common_csv, specific_csv

    def _write_common_csv(self, output_dir: Path) -> Path:
        """Write wide-format CSV: one row per block, columns for common parameters."""
        path = output_dir / "blocks_common_parameters.csv"
        param_names = self._common_parameter_names
        fieldnames = ["block", "type", "description", *param_names, "has_date"]

        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for sig in self.signatures:
                row: dict[str, Any] = {
                    "block": sig.block_name,
                    "type": sig.block_type,
                    "description": sig.description or "",
                }
                for name in param_names:
                    default = sig.common_parameters.get(name, {}).get("default")
                    row[name] = "" if default is None else default
                row["has_date"] = sig.has_date
                writer.writerow(row)

        return path

    def _write_specific_csv(self, output_dir: Path) -> Path:
        """Write long-format CSV: one row per (block, specific parameter)."""
        path = output_dir / "blocks_specific_parameters.csv"
        fieldnames = ["block", "parameter_name", "parameter_type", "default_value"]

        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for sig in self.signatures:
                for name, spec in sorted(sig.specific_parameters.items()):
                    writer.writerow(
                        {
                            "block": sig.block_name,
                            "parameter_name": name,
                            "parameter_type": spec.get("type", ""),
                            "default_value": ""
                            if spec.get("default") is None
                            else spec["default"],
                        }
                    )

        return path

    # -- export: Google Sheets ----------------------------------------------

    def to_gsheet(
        self,
        spreadsheet_key: str,
        common_sheet_name: str = "🔒 Blocks",
        specific_sheet_name: str = "🔒 Definitions",
    ) -> None:
        """Write common and specific parameters to a Google Spreadsheet.

        Parameters
        ----------
        spreadsheet_key : str
            The spreadsheet ID (the long string in the Google Sheets URL).
        common_sheet_name : str
            Worksheet name for the wide-format common-parameters table.
        specific_sheet_name : str
            Worksheet name for the long-format specific-parameters table.
        """
        import gspread  # type: ignore

        from requipso.google import get_user_credentials

        gc = gspread.authorize(get_user_credentials())
        spreadsheet = gc.open_by_key(spreadsheet_key)

        # --- specific parameters (Definitions) ---
        spec_header = [
            "block",
            "parameter_name",
            "parameter_type",
            "default_value",
            "description",
        ]
        spec_rows: list[list[str]] = [spec_header]
        spec_dicts: dict[str, dict[str, Any]] = {}
        for sig in self.signatures:
            spec_dicts[sig.block_name] = dict()
            for name, spec in sorted(sig.specific_parameters.items()):
                default = spec.get("default")
                spec_dicts[sig.block_name][name] = default
                spec_rows.append(
                    [
                        sig.block_name,
                        name,
                        spec.get("type", ""),
                        "" if default is None else str(default),
                        spec.get("description", ""),
                    ]
                )

        specific_ws = self._get_or_create_worksheet(
            spreadsheet, specific_sheet_name, len(spec_rows), len(spec_header)
        )
        specific_ws.clear()
        specific_ws.update(range_name=spec_rows, value_input_option="RAW")
        print(
            f"[info] Wrote {len(spec_rows) - 1} rows to sheet '{specific_sheet_name}'"
        )

        # --- common parameters (Blocks) ---
        param_names = self._common_parameter_names
        header = [
            "block",
            "type",
            "description",
            *param_names,
            "has_date",
            "supplementary_params",
        ]
        rows: list[list[str]] = [header]
        for sig in self.signatures:
            row: list[str] = [
                sig.block_name,
                sig.block_type,
                sig.description or "",
            ]
            for name in param_names:
                default = sig.common_parameters.get(name, {}).get("default")
                row.append("" if default is None else str(default))
            row.append(str(sig.has_date))

            specific_parameters = spec_dicts.get(sig.block_name, None)
            if specific_parameters:
                print(specific_parameters)
                specific_parameter_str = json.dumps(
                    spec_dicts.get(sig.block_name, None), ensure_ascii=False
                )
            else:
                specific_parameter_str = ""

            row.append(specific_parameter_str)
            rows.append(row)

        common_ws = self._get_or_create_worksheet(
            spreadsheet, common_sheet_name, len(rows), len(header)
        )
        common_ws.clear()
        common_ws.update(range_name=rows, value_input_option="RAW")
        print(f"[info] Wrote {len(rows) - 1} rows to sheet '{common_sheet_name}'")

    @staticmethod
    def _get_or_create_worksheet(
        spreadsheet: Any, title: str, rows: int, cols: int
    ) -> Any:
        """Return existing worksheet by *title*, or create it."""
        try:
            ws = spreadsheet.worksheet(title)
        except Exception:  # noqa: BLE001  — gspread raises WorksheetNotFound
            return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        if ws.row_count < rows or ws.col_count < cols:
            ws.resize(rows=max(ws.row_count, rows), cols=max(ws.col_count, cols))
        return ws


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: collect signatures, write CSVs, optionally print JSON."""
    parser = argparse.ArgumentParser(
        description="Export TableBlock signatures and parameters.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Also print JSON to stdout."
    )
    parser.add_argument(
        "--gsheet",
        metavar="SPREADSHEET_KEY",
        help="Write to a Google Spreadsheet (logs in with your Google account).",
        default=SHEET_ID,
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for generated CSV files (default: cwd).",
    )
    args = parser.parse_args()

    exporter = BlockExporter()
    # output_dir = Path(args.output_dir)

    # common_csv, specific_csv = exporter.to_csv(output_dir)
    # print(f"[info] Wrote {common_csv}")
    # print(f"[info] Wrote {specific_csv}")

    if args.json:
        print(exporter.to_json())

    if args.gsheet:
        exporter.to_gsheet(args.gsheet)

    for sig in exporter.signatures:
        print(f"{sig.module}.{sig.block_name} [{sig.block_type}] -> {sig.params_name}")


if __name__ == "__main__":
    main()
