"""Utility processors for block transformations.

This module contains reusable processors that can be composed with blocks,
replacing inheritance-based approaches (like the old RegexBlock mixin).
"""

from __future__ import annotations

from typing import Any, Iterable

import edsnlp
import edsnlp.pipes as eds
import polars as pl
from edsnlp.data.base import validate_schema_overrides
from edsnlp.data.converters import get_doc2dict_converter
from edsnlp.data.polars import PolarsWriter
from edsnlp.pipes import terminations
from edsnlp.utils.collections import flatten
from pydantic import Field, field_validator

from .params import MultiStringParam, TransformFunc


class LenientPolarsWriter(PolarsWriter):
    """PolarsWriter that tolerates `schema_overrides` columns missing from an
    empty result (edsnlp raises a ValueError in that case)."""

    def consolidate(self, items: Iterable[Any]):
        if self.dtypes is not None:
            return pl.from_dicts(flatten(items), schema=self.dtypes)
        res = pl.from_dicts(
            flatten(items), schema=self.schema, schema_overrides=self.schema_overrides
        )
        if not res.is_empty():
            validate_schema_overrides(res.columns, self.schema_overrides)
        return res


class RegexProcessor:
    """Processes text columns with edsnlp regex matching and qualifiers.

    Uses composition instead of inheritance - blocks can instantiate and use
    this processor in their transform() method.

    Example:
        class RegexATCD(TableBlock):
            def __init__(self, params: RegexATCDParams):
                super().__init__(params=params)
                self.processor = RegexProcessor(
                    pattern=params.pattern,
                    qualifiers=params.qualifiers,
                )

            def transform(self, antecedent: pl.DataFrame) -> pl.DataFrame:
                grouped = ...  # prepare data
                return self.processor.process(grouped, output_column_name=self.name)
    """

    def __init__(
        self,
        pattern: str | None,
        qualifiers: list[str] | None = None,
        pipe: str | None = None,
    ):
        """Initialize the regex processor.

        Args:
            pattern: Regex pattern to match (optional)
            qualifiers: NLP qualifiers to use (default: negation, hypothesis, family)
            pipe: Optional existing edsnlp pipe name to use instead of regex
        """
        self.pattern = pattern
        self.qualifiers = (
            qualifiers if qualifiers is not None else ["negation", "hypothesis"]
        )
        self.pipe = pipe

        termination = terminations.termination
        termination += ["\n-", "\n\t-"]  # Adding "-" as a "sentece-separator"

        nlp = edsnlp.blank("eds")
        nlp.add_pipe(eds.sentences())
        nlp.add_pipe(eds.normalizer())
        if self.pipe is not None:
            pipe_cls = getattr(eds, self.pipe)
            nlp.add_pipe(pipe_cls())
        else:
            nlp.add_pipe(
                eds.matcher(
                    regex={"regex": self.pattern} if self.pattern is not None else None,
                    attr="NORM",
                )
            )

        for qual in self.qualifiers:
            qual_pipe = getattr(eds, qual)
            nlp.add_pipe(qual_pipe(termination=termination))

        self.nlp = nlp

    def process(
        self,
        df: pl.DataFrame,
        id_column: str = "note_id",
        text_column: str = "note_text",
        output_column_name: str = "match",
        output_span_attribute_and_dtype: tuple[str, pl.DataType] | None = None,
    ) -> pl.DataFrame:
        """Process a DataFrame with regex matching using edsnlp.

        Args:
            df: Input DataFrame with text to process
            text_column: Name of the column containing text
            id_column: Name of the ID column (created if missing)
            output_column_name: Name of the output boolean column
            output_span_attribute_and_dtype: Name of the Span attribute to use for the output column and its dtype.
            If None, the lexical_variant is used and the dtype is String.

        Returns:
            DataFrame with the original columns plus output_column_name
        """

        df = df.with_columns(
            note_id=pl.col(id_column),
            note_text=pl.col(text_column),
        )

        docs = edsnlp.data.from_polars(
            df, converter="omop", doc_attributes=["patient_id"]
        )
        docs = docs.map_pipeline(self.nlp).set_processing(
            backend="multiprocessing",
            show_progress=True,
        )

        print(f"Use {self.nlp} to process {df.height} documents")

        if output_span_attribute_and_dtype is not None:
            output_span_attribute, output_span_dtype = output_span_attribute_and_dtype
        else:
            output_span_attribute = "lexical_variant"
            output_span_dtype = pl.String

        span_attributes = (
            self.qualifiers
            if output_span_attribute == "lexical_variant"
            else [*self.qualifiers, output_span_attribute]
        )

        schema_overrides = {
            **(
                {output_span_attribute: output_span_dtype}
                if output_span_attribute != "lexical_variant"
                else {}
            ),
            **{qualifier: pl.Boolean for qualifier in self.qualifiers},
        }

        converter, converter_kwargs = get_doc2dict_converter(
            "ents",
            dict(
                span_getter=["ents"],
                span_attributes=span_attributes,
                doc_attributes=["patient_id"],
            ),
        )
        ents: pl.DataFrame = (
            docs.map(converter, kwargs=converter_kwargs).write(
                LenientPolarsWriter(schema_overrides=schema_overrides)
            )
        ).with_columns(
            pl.col(pl.Int64).cast(pl.Int32),
        )
        print(f"Number of entities: {ents.height}")

        if ents.is_empty():
            ents = pl.DataFrame(
                [
                    pl.Series("note_id", [], dtype=pl.Int32),
                    pl.Series("start", [], dtype=pl.Int32),
                    pl.Series("end", [], dtype=pl.Int32),
                    pl.Series("label", [], dtype=pl.String),
                    pl.Series(output_span_attribute, [], dtype=output_span_dtype),
                    pl.Series("span_type", [], dtype=pl.String),
                    pl.Series("patient_id", [], dtype=pl.Int32),
                    *[
                        pl.Series(qualifier, [], dtype=pl.Boolean)
                        for qualifier in self.qualifiers
                    ],
                ]
            )

        if self.qualifiers:
            ents = ents.filter(~pl.any_horizontal(*[self.qualifiers]))

        ents = ents.with_columns(
            pl.col("note_id").alias(id_column),
            pl.col(output_span_attribute).alias(output_column_name),
        ).unique()

        return ents


class RegexParams(MultiStringParam):
    """Parameters for regex-based  blocks."""

    value: list[str] = Field(
        default=[],
        description="[HELP] regex / Liste de regex / pipe edsnlp (e.g. 'edsnlp.diabetes') à appliquer.",
    )
    qualifiers: list[str] = Field(
        default=["negation", "hypothesis"],
        description="NLP qualifiers to apply (e.g. negation, hypothesis).",
    )
    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation function."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one match."
    )

    @field_validator("value", mode="after")
    def check_if_value_is_edsnlp_pipe(cls, v):
        # Occurs after the default MultiStringParam validation, so self.value is already a list of strings
        if (not v) or (len(v) > 1):
            return (
                v  # If it's empty or has multiple values, we skip the edsnlp pipe check
            )

        if not v:
            return v

        pipe = v[0]  # At this stage, we know there is only one value
        if pipe.startswith("edsnlp."):
            pipe_name = pipe[len("edsnlp.") :]
            if pipe_name not in dir(eds):
                raise ValueError(
                    f"Specified edsnlp pipe '{pipe_name}' not found in edsnlp.pipes."
                )

        return v

    def get_regex_and_pipe(self) -> dict[str, str | None]:
        """Return a tuple of (regex_pattern, edsnlp_pipe) based on the value."""
        if not self.value:
            return {"pattern": None, "pipe": None}
        if len(self.value) == 1 and self.value[0].startswith("edsnlp."):
            return {"pattern": None, "pipe": self.value[0][len("edsnlp.") :]}
        regex_pattern = self.get_regex(case=False)
        return {"pattern": regex_pattern, "pipe": None}
