"""Consultation-related blocks.

These blocks operate on the consultation table.
"""

from __future__ import annotations

import polars as pl
from pydantic import Field

from .base import BlockConfig, OutputType, TableBlock
from .params import NoParams, TransformFunc

# =============================================================================
# Consultations
# =============================================================================


class ConsultationsParams(NoParams):
    """Parameters for Consultations block."""

    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation: count consultations."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one consultation."
    )
    consultation_motive_category_label: list[str] | None = Field(
        default=None, description="Filter by consultation motive category labels."
    )
    consultation_status_label: list[str] | None = Field(
        default=["Ended"], description="Filter by consultation status labels."
    )
    medical_center_initials: list[str] | None = Field(
        default=None, description="Filter by medical center initials."
    )
    health_professional_names: list[str] | None = Field(
        default=None,
        description="Filter by health professional name (format surname name).",
    )


class Consultations(TableBlock[ConsultationsParams]):
    """Returns the consultations for the patient."""

    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="event",
        date_column=("consultation_start_datetime", "consultation_end_datetime"),
        description="Retourne les consultations du patient.",
    )

    def transform(  # type: ignore[override]
        self,
        consultation: pl.DataFrame,
        medical_center: pl.DataFrame,
        health_professional: pl.DataFrame,
    ) -> pl.DataFrame:

        hp = health_professional.select(
            "health_professional_id",
            (
                pl.col("health_professional_first_name")
                + pl.lit(" ")
                + pl.col("health_professional_last_name")
            ).alias("health_professional_name"),
        )

        consultation = consultation.join(
            medical_center.select("medical_center_id", "medical_center_initials"),
            on="medical_center_id",
            how="inner",
        ).join(
            hp,
            on="health_professional_id",
            how="inner",
        )

        if self.params.consultation_motive_category_label:
            consultation = consultation.filter(
                pl.col("consultation_motive_category_label").is_in(
                    self.params.consultation_motive_category_label
                )
            )

        if self.params.consultation_status_label:
            consultation = consultation.filter(
                pl.col("consultation_status_label").is_in(
                    self.params.consultation_status_label
                )
            )

        if self.params.medical_center_initials:
            consultation = consultation.filter(
                pl.col("medical_center_initials").is_in(
                    self.params.medical_center_initials
                )
            )

        if self.params.health_professional_names:
            consultation = consultation.filter(
                pl.col("health_professional_name").is_in(
                    self.params.health_professional_names
                )
            )

        return consultation.select(
            "patient_id",
            "consultation_id",
            pl.lit(True).alias(self.name),
            "medical_center_initials",
            "health_professional_name",
            "consultation_motive_category_label",
            "consultation_status_label",
            self.start_date_column,
            self.end_date_column,
        )
