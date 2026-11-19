"""Biometry-related event blocks.

These blocks operate on the biometry table and produce multiple rows per patient
(one per measurement), which are then aggregated to patient level.
"""

from __future__ import annotations

import polars as pl
from pydantic import Field

from .base import BlockConfig, OutputType, TableBlock
from .params import BlockParams, StringParam, TransformFunc


MINMAX_VALUES: dict[str, tuple[float, float]] = {
    "temperature": (35, 41),
    "height": (30, 230),
    "waist_size": (20, 120),
    "heart_rate": (25, 220),
    "glycemia": (0.1, 10),
    "respiratory_rate": (5, 50),
    "cardio_fetal_rhythm": (25, 220),
    "blood_pressure_systolic": (30, 250),
    "weight": (1, 250),
    "blood_pressure_diastolic": (10, 150),
    "head_circumference": (20, 65),
    "uterine_height": (0, 40),
    "spo2": (60, 100),
    "peak_expiratory_flow": (50, 1000),
    "digital_visual_scale": (0, 10),
    "bmi": (10, 60),
}


class BiometryParams(StringParam):
    value: str = Field(
        description="[HELP] Label de la biométrie à extraire (e.g. 'weight', 'height', 'bmi'...).",
    )
    agg_func: TransformFunc = Field(
        default="LAST(x)", description="Aggregation: take the last measurement."
    )
    post_func: TransformFunc = Field(
        default="x", description="Post-transform: identity (return raw value)."
    )


class Biometry(TableBlock[BiometryParams]):
    """Returns a patient's biometry."""

    config = BlockConfig(
        output_type=OutputType.NUMBER,
        block_type="event",
        date_column="biometry_date",
        description="Retourne la biométrie demandée du patient.",
    )

    def get_bmi(self, biometry: pl.DataFrame, patient: pl.DataFrame) -> pl.DataFrame:
        # Allowable days diff between height and weight measurements for baby, minor and adult
        ALLOWABLE_DAYS_DIFF_FOR_BABY = 0
        ALLOWABLE_DAYS_DIFF_FOR_MINOR = 365
        ALLOWABLE_DAYS_DIFF_FOR_ADULT = 5 * 365

        column = "biometry_value"

        weight_df = biometry.filter(pl.col("biometry_label") == "weight").select(
            [
                "patient_id",
                pl.col(column).cast(float).alias("weight"),
                pl.col("biometry_date").alias("weight_dt"),
            ]
        )

        height_df = biometry.filter(pl.col("biometry_label") == "height").select(
            [
                "patient_id",
                pl.col(column).cast(float).alias("height"),
                pl.col("biometry_date").alias("height_dt"),
            ]
        )

        # Get all combinations
        result = weight_df.join(height_df, on="patient_id", how="inner")

        # Find the height with minimum time difference
        result = (
            result.with_columns(
                (pl.col("weight_dt") - pl.col("height_dt")).abs().alias("time_diff")
            )
            .group_by(["patient_id", "weight", "weight_dt"])
            .agg(
                [
                    pl.col("height").sort_by("time_diff").first(),
                    pl.col("height_dt").sort_by("time_diff").first(),
                ]
            )
        )

        result = result.with_columns(
            (pl.col("height_dt") - pl.col("weight_dt"))
            .dt.total_days()
            .abs()
            .alias("time_diff_days")
        )

        # Add age of patient at height measurement
        result = (
            result.join(
                patient.select("patient_id", "patient_birth_date"),
                on="patient_id",
                how="left",
            )
            .with_columns(
                (
                    (pl.col("height_dt") - pl.col("patient_birth_date")).dt.total_days()
                    / 365.25
                ).alias("age_at_height")
            )
            .drop("patient_birth_date")
        )

        result = result.with_columns(
            is_valid=(
                (
                    (pl.col("age_at_height") < 1)
                    & (pl.col("time_diff_days") < ALLOWABLE_DAYS_DIFF_FOR_BABY)
                )
                | (
                    ((pl.col("age_at_height") >= 1) & (pl.col("age_at_height") <= 18))
                    & (pl.col("time_diff_days") < ALLOWABLE_DAYS_DIFF_FOR_MINOR)
                )
                | (
                    (pl.col("age_at_height") > 18)
                    & (pl.col("time_diff_days") < ALLOWABLE_DAYS_DIFF_FOR_ADULT)
                )
            )
        )

        result = result.filter(pl.col("is_valid")).drop("is_valid")

        # compute BMI
        result = result.select(
            "patient_id",
            (pl.col("weight") / (pl.col("height") / 100) ** 2).alias(self.name),
            pl.col("weight_dt").alias(self.start_date_column),
        )

        return result

    def transform(self, biometry: pl.DataFrame, patient: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        column = "biometry_value"
        biometry_label = self.params.value

        if biometry_label == "bmi":
            results = self.get_bmi(biometry, patient)
        else:
            biometry_filtered = biometry.filter(
                pl.col("biometry_label") == biometry_label
            )
            results = biometry_filtered.select(
                "patient_id",
                pl.col(column).alias(self.name),
                pl.col(self.start_date_column),
            )
        min_val, max_val = MINMAX_VALUES.get(biometry_label, (None, None))
        if min_val is not None and max_val is not None:
            results = results.filter(
                (pl.col(self.name) >= min_val) & (pl.col(self.name) <= max_val)
            )
        return results
