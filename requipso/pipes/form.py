"""Form-related event blocks.

These blocks operate on the form and form_answer tables and produce one row per
completed form, which are then aggregated to patient level.
"""

from __future__ import annotations

import polars as pl
from pydantic import Field

from .base import BlockConfig, OutputType, TableBlock
from .params import StringParam, TransformFunc

MAIN_ANSWER_LABEL = "score"


class FormulaireParams(StringParam):
    value: str = Field(
        description="[HELP] Nom du formulaire (e.g. 'PHQ-9', 'GAD-7', 'EPWORTH'...).",
    )
    agg_func: TransformFunc = Field(
        default="LAST(x)", description="Aggregation: take the last completed form."
    )
    post_func: TransformFunc = Field(
        default="x", description="Post-transform: identity (return raw score)."
    )


class Formulaire(TableBlock[FormulaireParams]):
    """Returns the main answer (score) of a patient's form."""

    config = BlockConfig(
        output_type=OutputType.NUMBER,
        block_type="event",
        date_column="form_completed_at",
        description="Retourne la réponse principale (score) du formulaire demandé.",
    )

    def transform(  # type: ignore[override]
        self,
        form: pl.DataFrame,
        form_answer: pl.DataFrame,
    ) -> pl.DataFrame:
        forms = form.filter(pl.col("form_name") == self.params.value)
        scores = form_answer.filter(
            pl.col("form_answer_label") == MAIN_ANSWER_LABEL
        ).select(
            "form_answer_id",
            "form_answer_value",
            "form_completed_at",
        )

        return forms.join(scores, on="form_id", how="inner").select(
            "patient_id",
            pl.col("form_answer_value").alias(self.name),
            "form_completed_at",
        )
