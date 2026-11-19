"""Prescription-related blocks.

These blocks operate on the drug_prescription table.
"""

from __future__ import annotations

import polars as pl
from pydantic import Field, field_validator

from .base import BlockConfig, OutputType, TableBlock
from .params import MultiStringParam, TransformFunc
from .processors import RegexParams, RegexProcessor

# =============================================================================
# Parameter Classes
# =============================================================================


class PrescriptionATCParams(MultiStringParam):
    """Parameters for PrescriptionATC block."""

    value: list[str] = Field(
        default=[],
        description="[HELP] ATC / ATCs séparés de '|' / Liste de ATCs.",
    )
    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation function."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one match."
    )


# =============================================================================
# PrescriptionATC
# =============================================================================


class PrescriptionATC(TableBlock[PrescriptionATCParams]):
    """Returns a boolean indicating if there's a prescription matching an ATC code."""

    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="event",
        date_column=("drug_posology_start_date", "drug_posology_end_date"),
        description="Retourne un booléen indiquant si on a un match de la recherche dans les prescription sur le code ATC.",
    )

    def __init__(self, params: PrescriptionATCParams, name: str | None = None):
        super().__init__(name=name, params=params)

    def transform(  # type: ignore[override]
        self,
        drug_prescription: pl.DataFrame,
        drug_posology: pl.DataFrame,
    ) -> pl.DataFrame:
        codes = self.params.get_regex(case=True, prefix=True)

        df = drug_posology.select(
            "drug_prescription_id",
            self.start_date_column,
            self.end_date_column,
        ).join(
            drug_prescription.filter(
                pl.col("drug_prescription_atc").str.contains(codes)
            ).select(
                "patient_id",
                "drug_prescription_id",
                pl.col("drug_prescription_atc").alias(self.name),
            ),
            on="drug_prescription_id",
            how="inner",
        )
        return df


class RegexPrescriptionParams(RegexParams):
    """Parameters for regex-based patient observation blocks."""

    pass


class RegexPrescription(TableBlock[RegexPrescriptionParams]):
    """Returns a boolean indicating if there's a regex match on the patient's medical history."""

    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="event",
        date_column=("drug_posology_start_date", "drug_posology_end_date"),
        description="Retourne un booléen indiquant si on a un match de la recherche dans les prescriptions (nom commercial ou dénomination officielle).",
    )

    def __init__(
        self,
        params: RegexPrescriptionParams,
        name: str | None = None,
    ):
        super().__init__(name=name, params=params)
        processor_params = params.get_regex_and_pipe()
        self.processor = RegexProcessor(
            pattern=processor_params["pattern"],
            qualifiers=params.qualifiers,
            pipe=processor_params["pipe"],
        )

    def transform(  # type: ignore[override]
        self,
        drug_prescription: pl.DataFrame,
        drug_posology: pl.DataFrame,
    ) -> pl.DataFrame:
        notes = drug_prescription.select(
            "patient_id",
            "drug_prescription_id",
            drug_prescription_text=(
                pl.col("drug_prescription_name").fill_null("")
                + pl.lit("   ")
                + pl.col("drug_prescription_common_name").fill_null("")
            ),
        )

        posology = drug_posology.select(
            "drug_prescription_id",
            self.start_date_column,
            self.end_date_column,
        )

        result = self.processor.process(
            notes,
            id_column="drug_prescription_id",
            text_column="drug_prescription_text",
            output_column_name=self.name,
        )
        return result.join(posology, on="drug_prescription_id", how="inner")
