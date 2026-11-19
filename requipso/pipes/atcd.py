"""Antecedent (medical history) related blocks.

These blocks use composition with RegexProcessor instead of inheritance.
"""

from __future__ import annotations

import polars as pl
from pydantic import Field, field_validator

from .base import BlockConfig, OutputType, TableBlock
from .params import MultiStringParam, TransformFunc
from .processors import RegexParams, RegexProcessor


class RegexPatientObservationParams(RegexParams):
    """Parameters for regex-based patient observation blocks."""

    patient_observation_label: list[str] = Field(
        default=[
            "medical_background_data",
            "lifestyle_data",
            "allergies_data",
            "chirurgical_background_data",
            "prevention_data",
        ],
        description="Patient observation labels to search through.",
    )

    @field_validator("patient_observation_label", mode="before")
    @classmethod
    def parse_patient_observation_label(cls, v):
        if isinstance(v, str):
            return [v]
        return v


class RegexConsultationParams(RegexParams):
    """Parameters for regex-based consultation blocks."""

    pass


class CISP2Params(MultiStringParam):
    """Parameters for CISP2 block."""

    value: list[str] = Field(
        default=[],
        description="[HELP] Code CISP2 / Codes CISP2 séparés de '|' / Liste de codes CISP2",
    )
    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation function."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one match."
    )


class CIM10Params(MultiStringParam):
    """Parameters for CIM10 block."""

    value: list[str] = Field(
        default=[],
        description="[HELP] Code CIM10 / Codes CIM10 séparés de '|' / Liste de codes CIM10",
    )
    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation function."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one match."
    )


# =============================================================================
# RegexATCD
# =============================================================================


class RegexPatientObservation(TableBlock[RegexPatientObservationParams]):
    """Returns a boolean indicating if there's a regex match on the patient's medical history."""

    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="event",
        description="Retourne les entités extraites des notes d'observations du patient correspondant à la regex ou à la pipe edsnlp spécifiée.",
    )

    def __init__(
        self,
        params: RegexPatientObservationParams,
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
        patient_observation: pl.DataFrame,
    ) -> pl.DataFrame:
        notes = patient_observation.filter(
            pl.col("patient_observation_label").is_in(
                self.params.patient_observation_label
            )
        )

        result = self.processor.process(
            notes,
            id_column="patient_observation_id",
            text_column="patient_observation_value",
            output_column_name=self.name,
        )
        return result


class RegexConsultation(TableBlock[RegexConsultationParams]):
    """Returns a boolean indicating if there's a regex match on the patient's medical history."""

    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="event",
        date_column=("consultation_start_datetime", "consultation_end_datetime"),
        description="Retourne les entités extraites des notes de consultation du patient correspondant à la regex ou à la pipe edsnlp spécifiée.",
    )

    def __init__(
        self,
        params: RegexConsultationParams,
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
        consultation: pl.DataFrame,
    ) -> pl.DataFrame:
        notes = consultation.select(
            "patient_id",
            "consultation_id",
            consultation_text=(
                pl.lit("## OBSERVATION ##\n\n")
                + pl.col("consultation_observation")
                + pl.lit("\n\n## CONCLUSION ##\n\n")
                + pl.col("consultation_conclusion")
            ),
        )

        result = self.processor.process(
            notes,
            id_column="consultation_id",
            text_column="consultation_text",
            output_column_name=self.name,
        )

        result = result.join(
            consultation.select(
                "consultation_id",
                self.start_date_column,
                self.end_date_column,
            ),
            on="consultation_id",
            how="inner",
        )

        return result


# =============================================================================
# CISP2
# =============================================================================


class CISP2(TableBlock[CISP2Params]):
    """Returns a boolean indicating if the patient has a medical history matching a CISP2 code."""

    config = BlockConfig(
        output_type=OutputType.CATEGORY,
        block_type="event",
        date_column=("condition_start_date", "condition_end_date"),
        description="Retourne, à partir des antécédents d'un patient, les codes CISP2 correspondant.",
    )

    def __init__(self, params: CISP2Params, name: str | None = None):
        super().__init__(name=name, params=params)

    def transform(  # type: ignore[override]
        self,
        concept: pl.DataFrame,
        concept_relationship: pl.DataFrame,
        patient_condition: pl.DataFrame,
        patient_observation: pl.DataFrame,
        patient_condition_date: pl.DataFrame,
    ) -> pl.DataFrame:
        codes = self.params.get_regex(case=True, prefix=True)

        cisp = (
            concept.filter(
                pl.col("concept_vocabulary") == "cisp",
            )
            .filter(
                pl.col("concept_code").str.contains(codes),
            )
            .select(
                pl.col("concept_id").alias("concept_id_1"),
                pl.col("concept_code").alias(self.name),
            )
        )

        ipso_patho = concept.filter(
            pl.col("concept_vocabulary") == "ipso_pathology",
        ).select(
            pl.col("concept_id").alias("concept_id_2"),
        )

        mapped = (
            concept_relationship.join(cisp, on="concept_id_1", how="inner")
            .join(ipso_patho, on="concept_id_2", how="inner")
            .select(
                pl.col("concept_id_2").alias("condition_concept_id"), pl.col(self.name)
            )
        )

        date_ranges = patient_condition_date.group_by("patient_condition_id").agg(
            pl.col("patient_condition_date").min().alias("condition_start_date"),
            pl.col("patient_condition_date").max().alias("condition_end_date"),
        )

        kept_patient_condition = (
            patient_condition.filter(pl.col("condition_concept_type") == "pathology")
            .join(
                patient_observation.filter(
                    pl.col("patient_observation_label").is_in(
                        [
                            "gynecologic_background_data",
                            "chirurgical_background_data",
                            "medical_background_data",
                        ]
                    )
                ).select("patient_observation_id"),
                on="patient_observation_id",
                how="inner",
            )
            .join(
                mapped,
                on="condition_concept_id",
                how="inner",
            )
            .join(
                date_ranges,
                on="patient_condition_id",
                how="left",
            )
        )

        return kept_patient_condition.select(
            "patient_id",
            self.name,
            self.start_date_column,
            self.end_date_column,
        ).unique()


# =============================================================================
# CIM10
# =============================================================================


class CIM10(TableBlock[CIM10Params]):
    """Returns a boolean indicating if the patient has a medical history matching a CIM10 code."""

    config = BlockConfig(
        output_type=OutputType.CATEGORY,
        block_type="event",
        date_column=("condition_start_date", "condition_end_date"),
        description="Retourne, à partir des antécédents d'un patient, les codes CIM10 correspondant.",
    )

    def __init__(self, params: CIM10Params, name: str | None = None):
        super().__init__(name=name, params=params)

    def transform(  # type: ignore[override]
        self,
        concept: pl.DataFrame,
        concept_relationship: pl.DataFrame,
        patient_condition: pl.DataFrame,
        patient_observation: pl.DataFrame,
        patient_condition_date: pl.DataFrame,
    ) -> pl.DataFrame:
        codes = self.params.get_regex(case=True, prefix=True)

        cim10 = (
            concept.filter(
                pl.col("concept_vocabulary") == "cim10",
            )
            .filter(
                pl.col("concept_code").str.contains(codes),
            )
            .select(
                pl.col("concept_id").alias("concept_id_1"),
                pl.col("concept_code").alias(self.name),
            )
        )

        ipso_patho = concept.filter(
            pl.col("concept_vocabulary") == "ipso_pathology",
        ).select(
            pl.col("concept_id").alias("concept_id_2"),
        )

        mapped = (
            concept_relationship.join(cim10, on="concept_id_1", how="inner")
            .join(ipso_patho, on="concept_id_2", how="inner")
            .select(
                pl.col("concept_id_2").alias("condition_concept_id"), pl.col(self.name)
            )
        )

        date_ranges = patient_condition_date.group_by("patient_condition_id").agg(
            pl.col("patient_condition_date").min().alias("condition_start_date"),
            pl.col("patient_condition_date").max().alias("condition_end_date"),
        )

        kept_patient_condition = (
            patient_condition.filter(pl.col("condition_concept_type") == "pathology")
            .join(
                patient_observation.filter(
                    pl.col("patient_observation_label").is_in(
                        [
                            "gynecologic_background_data",
                            "chirurgical_background_data",
                            "medical_background_data",
                        ]
                    )
                ).select("patient_observation_id"),
                on="patient_observation_id",
                how="inner",
            )
            .join(
                mapped,
                on="condition_concept_id",
                how="inner",
            )
            .join(
                date_ranges,
                on="patient_condition_id",
                how="left",
            )
        )

        return kept_patient_condition.select(
            "patient_id",
            self.name,
            self.start_date_column,
            self.end_date_column,
        ).unique()
