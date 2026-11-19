"""Pydantic parameter models for block configuration.

Hierarchy::

    BlockParams          -- common fields shared by every block
    ├── NoParams         -- blocks that need no user configuration
    ├── StringParam      -- single string value
    ├── NumberParam      -- single numeric value
    ├── MultiStringParam -- list of strings (accepts ``"a|b|c"`` shorthand)
    ├── CategoryParam    -- string constrained to an allowed set
    └── CombineOperatorParam -- AND/OR operator for CombinedBlock
"""

from __future__ import annotations

import ast
import json
import logging
from functools import partial
from typing import Any, Callable, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlglot import exp, parse_one

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

TransformFunc = Callable[[pl.Expr], pl.Expr] | None  # | str | None
"""A column transform: either a SQL expression referencing ``x`` or a callable."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sql_to_polars_expr(col: pl.Expr, sql: str) -> pl.Expr:
    """Convert a SQL expression that references ``x`` into a Polars expression.

    ``x`` is replaced by the actual column name carried by *col*.
    Double quotes are normalised to single quotes so that sqlglot treats
    string literals correctly.
    """
    expression = parse_one(sql.replace('"', "'"))

    def rename_column(node: exp.Expression) -> exp.Expression:
        if isinstance(node, exp.Column) and node.name == "x":
            return exp.column(col.meta.output_name())
        return node

    expr: pl.Expr = pl.sql_expr(expression.transform(rename_column).sql())
    return expr


# =========================================================================
# BlockParams — base class
# =========================================================================


class BlockParams(BaseModel):
    """Common parameters inherited by every block.

    Subclasses may override ``value`` to narrow its type or change its
    default, and may add extra fields for block-specific configuration.

    Attributes
    ----------
    value : Any
        The primary user-supplied value for the block.
    agg_func : TransformFunc
        SQL expression (use ``x`` for the column) **or** callable applied
        during aggregation.  Example: ``"COUNT(x)"``.
    post_func : TransformFunc
        SQL expression **or** callable applied *after* aggregation.
        Example: ``"x > 0"``.
    date_sql : str | None
        SQL filter using ``start_date``, ``end_date``, and/or ``reference_date``.
    reference_date_block : Any
        Another block whose result supplies per-patient reference dates.
    reference_date_sql : str | None
        SQL expression (e.g. ``"MIN(start_date)"``) that derives the
        reference date from the block's own dates.
    """

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        validate_default=True,
        coerce_numbers_to_str=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_sheet_values(cls, data: Any) -> Any:
        """Pre-process raw string values coming from spreadsheet cells.

        Handles empty-string removal (so field defaults apply), JSON/literal
        parsing for array and object strings, and boolean string coercion.
        """
        if not isinstance(data, dict):
            return data

        for key in list(data):
            val = data[key]
            if val is None:
                del data[key]
                continue
            if not isinstance(val, str):
                continue
            stripped = val.strip()
            if not stripped:
                del data[key]
                continue

            if stripped.startswith(("[", "{")):
                for parser in (
                    json.loads,
                    lambda s: json.loads(s.replace("'", '"')),
                    ast.literal_eval,
                ):
                    try:
                        data[key] = parser(stripped)
                        break
                    except (json.JSONDecodeError, ValueError, SyntaxError):
                        continue
                else:
                    data[key] = stripped
                continue

            low = stripped.lower()
            if low in ("true", "false"):
                data[key] = low == "true"
                continue

            data[key] = stripped

        return data

    value: Any = Field(description="Primary user-supplied value for the block.")
    agg_func: TransformFunc = Field(
        default=None,
        description='SQL expression (use "x" for the column) or callable applied during aggregation. Example: "COUNT(x)".',
    )
    post_func: TransformFunc = Field(
        default=None,
        description='SQL expression or callable applied after aggregation. Example: "x > 0".',
    )
    date_sql: str | None = Field(
        default=None,
        description="SQL filter using start_date, end_date, and/or reference_date.",
    )
    reference_date_block: Any = Field(
        default=None,
        description="Another block whose result supplies per-patient reference dates.",
    )
    reference_date_sql: str | None = Field(
        default=None,
        description='SQL expression deriving the reference date. Example: "MIN(start_date)".',
    )

    @field_validator("agg_func", "post_func", mode="before")
    @classmethod
    def parse_func(cls, func: TransformFunc | str) -> TransformFunc:
        """Accept a SQL string or callable; validate and wrap SQL strings."""
        if func is None:
            return None
        if isinstance(func, str):
            pl.sql_expr(func)  # validate early
            return partial(sql_to_polars_expr, sql=func)
        return func

    @field_validator("date_sql", "reference_date_sql", mode="before")
    @classmethod
    def validate_date_sql(cls, sql: str | None) -> str | None:
        """Ensure date SQL expressions reference ``start_date`` or ``end_date``."""
        if sql is None:
            return None
        if "start_date" not in sql and "end_date" not in sql:
            raise ValueError("Must contain 'start_date' or 'end_date'")
        pl.sql_expr(sql)  # validate early
        return sql


# =========================================================================
# Concrete parameter types
# =========================================================================


class NoParams(BlockParams):
    """For blocks that require no user configuration."""

    value: None = Field(default=None, description=None)


class StringParam(BlockParams):
    """Single required string value."""

    value: str = Field(description="Single string value.")


class NumberParam(BlockParams):
    """Single required numeric value."""

    value: int = Field(description="Single numeric value.")


class MultiStringParam(BlockParams):
    """List of strings.

    Accepts either a Python list or a pipe-separated string
    (e.g. ``"cardio|neuro"``).
    """

    value: list[str] = Field(
        default=[], description="List of strings (accepts pipe-separated input)."
    )

    @field_validator("value", mode="before")
    @classmethod
    def parse_pipe_separated(cls, v: str | list[str] | None) -> list[str]:
        """Split ``"a|b|c"`` into ``["a", "b", "c"]``."""
        if isinstance(v, str):
            return [c.strip() for c in v.split("|") if c.strip()]
        return v or []

    def get_regex(
        self, case: bool = True, prefix: bool = False, exact: bool = False
    ) -> str:
        """Build a regex that matches any of the stored values.

        Parameters
        ----------
        case : bool
            If *False*, prepends the ``(?i)`` flag.
        prefix : bool
            If *True*, only matches from the start (prefix match);
            otherwise matches anywhere
        exact : bool
            If *True*, matches exact words only;
            otherwise matches anywhere
        """

        if exact and prefix:
            raise ValueError("exact and prefix cannot be True at the same time")
        pattern = "|".join(self.value)
        if prefix:
            pattern = f"^(?:{pattern})"
        elif exact:
            pattern = f"^({pattern})$"
        else:
            pattern = f"({pattern})"
        if not case:
            pattern = f"(?i){pattern}"
        return pattern


class CategoryParam(BlockParams):
    """String value constrained to a fixed set of allowed choices."""

    value: str = Field(description="Selected value (must be in allowed list).")
    allowed: list[str] = Field(description="Allowed values for this parameter.")

    @field_validator("value")
    @classmethod
    def validate_choice(cls, v: str, info: Any) -> str:
        """Reject values not present in *allowed*."""
        allowed = info.data.get("allowed", [])
        if allowed and v not in allowed:
            raise ValueError(f"{v} not in allowed values: {allowed}")
        return v


class CombineOperatorParam(BlockParams):
    """AND/OR operator used by :class:`CombinedBlock`."""

    value: None = Field(default=None, description=None)
    operator: Literal["AND", "OR"] = Field(
        default="AND", description="Logical operator: AND or OR."
    )
