"""Patient-level blocks.

These blocks operate on the patient table and produce one row per patient.
"""

from __future__ import annotations

import datetime

import polars as pl
from pydantic import Field
from spacy.tokens import Span

from .base import BlockConfig, OutputType, TableBlock
from .params import MultiStringParam, NoParams, TransformFunc
from .processors import RegexProcessor

# =============================================================================
# Age
# =============================================================================


class AgeParams(NoParams):
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x>=18",
        description="Post-transform: True if the patient is an adult (18+).",
    )


class Age(TableBlock[AgeParams]):
    config = BlockConfig(
        output_type=OutputType.NUMBER,
        block_type="patient",
        date_column="patient_birth_date",
        description="Retourne l'âge du patient en années au moment de la référence.",
    )

    def transform(self, patient: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        if self.reference_date is None:
            raise ValueError("Reference date is required for Age block")
        return patient.join(
            self.reference_date,
            on="patient_id",
            how="left",
        ).select(
            "patient_id",
            (
                (
                    pl.col("reference_date") - pl.col("patient_birth_date")
                ).dt.total_days()
                / 365
            )
            .round(1)
            .alias(self.name),
            self.start_date_column,
        )


# =============================================================================
# EstVivant
# =============================================================================
class EstVivantParams(NoParams):
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x", description="Post-transform: True if the patient is alive."
    )


class EstVivant(TableBlock[EstVivantParams]):
    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="patient",
        date_column="patient_death_date",
        description="Retourne un booléen indiquant si le patient est vivant.",
    )

    def transform(self, patient: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        if self.reference_date is None:
            raise ValueError("Reference date is required for EstVivant block")
        patient = patient.join(
            self.reference_date,
            on="patient_id",
            how="left",
        )
        return patient.select(
            "patient_id",
            (
                (pl.col("reference_date") < pl.col("patient_death_date"))
                | pl.col("patient_death_date").is_null()
            ).alias(self.name),
            self.start_date_column,
        )


# =============================================================================
# MedecinTraitant
# =============================================================================


class MedecinTraitantParams(NoParams):
    mtr_only: bool = Field(
        default=True,
        description="If True, only include médecins traitants renforcés (MTR).",
    )
    include_external: bool = Field(
        default=False, description="If True, include external médecins traitants."
    )
    agg_func: TransformFunc = Field(  # type: ignore[assignment]
        default="COUNT(x)", description="Aggregation: count MT periods."
    )
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x>=1", description="Post-transform: True if at least one MT period."
    )


class MedecinTraitant(TableBlock[MedecinTraitantParams]):
    config = BlockConfig(
        output_type=OutputType.BOOLEAN,
        block_type="event",
        date_column=("regular_doctor_start_date", "regular_doctor_end_date"),
        description="Retourne les périodes de MT / MTR du patient (selon paramètres)",
    )

    def transform(self, regular_doctor_history: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        result = regular_doctor_history.filter(
            pl.col("health_professional_id").is_not_null(),
        )

        if not self.params.include_external:
            result = result.filter(~pl.col("regular_doctor_is_external"))

        if self.params.mtr_only:
            result = result.filter(pl.col("regular_doctor_is_mtr"))

        return result.select(
            "patient_id",
            pl.lit(True).alias(self.name),
            self.start_date_column,
            self.end_date_column,
        )


# =============================================================================
# Fumeur
# =============================================================================


class PaquetAnneesParams(NoParams):
    use_nlp: bool = Field(
        default=True,
        description="""
        If True, use the NLP to extract the smoking information from the patient's observations.
        In this case, the smoking start and end dates are not used.""",
    )
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x>0",
        description="Post-transform: True if the patient has smoked more than 0 pack-years.",
    )


class PaquetAnnees(TableBlock[PaquetAnneesParams]):
    config = BlockConfig(
        output_type=OutputType.NUMBER,
        block_type="patient",
        date_column=("smoking_start_date", "smoking_end_date"),
        description="Retourne le nombre de paquets-annees (smoking_pack_years) du patient renseignée dans l'EMR",
    )

    def transform(
        self,
        smoking: pl.DataFrame,
        patient_observation: pl.DataFrame,
    ) -> pl.DataFrame:  # type: ignore[override]
        if self.reference_date is None:
            raise ValueError("Reference date is required for PaquetAnnees block")

        smoking_patient_ids = smoking.select("patient_id").unique()

        if self.params.use_nlp:
            # If we use nlp, we have no date informations
            # So we use the current date
            reference_date = self.reference_date.select(
                "patient_id",
                pl.lit(datetime.datetime.now(tz=datetime.UTC)).alias("reference_date"),
            )
        else:
            reference_date = self.reference_date

        smoking = smoking.join(reference_date, on="patient_id", how="inner")
        # Keep only smoking before reference date
        smoking = smoking.filter(
            pl.col("smoking_start_date") < pl.col("reference_date")
        )
        smoking = smoking.with_columns(
            new_smoking_end_date=pl.when(pl.col("smoking_end_date").is_null())
            .then(pl.col("reference_date"))
            .otherwise(pl.min_horizontal("smoking_end_date", "reference_date")),
        ).with_columns(
            is_current_smoker=pl.col("new_smoking_end_date")
            >= pl.col("reference_date"),
        )

        smoking = (
            smoking.filter(pl.col("smoking_product") == "cigarette")
            .with_columns(
                pack_years=(
                    (pl.col("smoking_cigarettes_per_day") / 20)
                    * (
                        pl.col("new_smoking_end_date") - pl.col("smoking_start_date")
                    ).dt.total_days()
                    / 365
                )
            )
            .group_by("patient_id")
            .agg(
                pl.sum("pack_years").round(1),
                pl.min("smoking_start_date"),
                pl.max("smoking_end_date"),
            )
        )
        smoking = smoking.join(
            smoking_patient_ids, on="patient_id", how="right"
        ).select(
            "patient_id",
            pl.col("pack_years").fill_null(0).alias(self.name),
            pl.col("smoking_start_date").alias(self.start_date_column),
            pl.col("smoking_end_date").alias(self.end_date_column),
        )

        if not self.params.use_nlp:
            return smoking

        notes = patient_observation.filter(
            patient_observation_label="lifestyle_data",
        ).select(
            "patient_id",
            "patient_observation_id",
            "patient_observation_value",
        )

        def get_pa(span):
            pa = span._.assigned.get("PA", None)
            if pa is None:
                return None
            return float(pa.text.replace(",", ".").strip())

        Span.set_extension("PA", getter=get_pa, force=True)

        processor = RegexProcessor(
            pattern=None,
            qualifiers=[],
            pipe="tobacco",
        )
        smoking_nlp = (
            processor.process(
                df=notes,
                id_column="patient_observation_id",
                text_column="patient_observation_value",
                output_span_attribute_and_dtype=("PA", pl.Float64),
                output_column_name="pack_years",
            )
            .select(
                "patient_id",
                pl.col("pack_years").alias(self.name),
                pl.lit(None).alias(self.start_date_column),
                pl.lit(None).alias(self.end_date_column),
            )
            .filter(pl.col(self.name).is_not_null())
        )
        smoking_nlp_only = smoking_nlp.join(
            smoking_patient_ids,
            on="patient_id",
            how="anti",  # Anti join to keep patient with NLP but without structured
        )

        return pl.concat([smoking, smoking_nlp_only.cast(smoking.schema)])  # type: ignore[arg-type]


# =============================================================================
# Departement
# =============================================================================


class DepartementParams(MultiStringParam):
    value: list[str] = Field(
        default=[],
        description="[HELP] Département / Départements séparés de '|' / Liste de départements.",
    )
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x IS NOT NULL",
        description="[Post-transform: True if patient is in one of the specified departments.]",
    )


class Departement(TableBlock[DepartementParams]):
    config = BlockConfig(
        output_type=OutputType.STRING,
        block_type="patient",
        description="Retourne le département du patient.",
    )

    def transform(self, patient: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        if not self.params.value:
            result = patient
        else:
            result = patient.filter(
                pl.col("patient_residence_postal_code")
                .str.slice(0, 2)
                .is_in(self.params.value)
            )
        return result.select(
            "patient_id",
            pl.col("patient_residence_postal_code").alias(self.name),
        )


# =============================================================================
# CodePostal
# =============================================================================


class CodePostalParams(MultiStringParam):
    value: list[str] = Field(
        default=[],
        description="[HELP] CP / CPs séparés de '|' / Liste de CPs.",
    )
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x IS NOT NULL",
        description="Post-transform: True if patient is in one of the specified postal codes.",
    )


class CodePostal(TableBlock[CodePostalParams]):
    """Returns the patient's postal code."""

    config = BlockConfig(
        output_type=OutputType.STRING,
        block_type="patient",
        description="Retourne le code postal du patient.",
    )

    def transform(self, patient: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        if not self.params.value:
            result = patient
        else:
            result = patient.filter(
                pl.col("patient_residence_postal_code").is_in(self.params.value)
            )
        return result.select(
            "patient_id",
            pl.col("patient_residence_postal_code").alias(self.name),
        )


# =============================================================================
# Genre
# =============================================================================


class GenreParams(NoParams):
    post_func: TransformFunc = Field(  # type: ignore[assignment]
        default="x=='féminin'",
        description="Post-transform: True if the patient is female.",
    )


class Genre(TableBlock[GenreParams]):
    config = BlockConfig(
        output_type=OutputType.CATEGORY,
        block_type="patient",
        description="Retourne le genre déclaré du patient.",
    )

    def transform(self, patient: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        return patient.select(
            "patient_id",
            pl.col("patient_gender_label").alias(self.name),
        )
