from __future__ import annotations

import polars as pl
from pydantic import Field, field_validator

from .base import BlockConfig, OutputType, TableBlock
from .params import MultiStringParam, TransformFunc


class ALDParams(MultiStringParam):
    value: list[str] = Field(
        default=[],
        description="[HELP] Code ALD / Codes ALD séparés de '|' / Liste de codes ALD",
    )
    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation function."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one match."
    )

    @field_validator("value", mode="after")
    @classmethod
    def pad_with_zeros(cls, v: list[str]) -> list[str]:
        """Pad single-digit codeswith zeros to make 2 digits."""
        cleaned = []
        for code in v:
            splitted = code.split(".", maxsplit=2)
            prefix = splitted[0]
            if len(prefix) == 1:
                cleaned.append(f"0{code}")
            else:
                cleaned.append(code)
        return cleaned


class ALD(TableBlock[ALDParams]):
    config = BlockConfig(
        output_type=OutputType.CATEGORY,
        block_type="event",
        date_column=("patient_ald_start_date", "patient_ald_end_date"),
        description="Retourne les codes ALD du patient matchant les critères spécifiés.",
    )

    def __init__(self, params: ALDParams, name: str | None = None):
        super().__init__(name=name, params=params)

    def transform(self, patient_ald: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        codes = self.params.get_regex(case=True, exact=True)
        return patient_ald.filter(
            pl.col("patient_ald_code").str.contains(codes).fill_null(False)
        ).select(
            "patient_id",
            pl.col("patient_ald_code").alias(self.name),
            self.start_date_column,
            self.end_date_column,
        )


class InsuranceParams(MultiStringParam):
    value: list[str] = Field(
        default=[],
        description="[HELP] Type d'assurance / Types d'assurance séparés de '|' / Liste de types d'assurance",
    )
    agg_func: TransformFunc = Field(
        default="COUNT(x)", description="Aggregation function."
    )
    post_func: TransformFunc = Field(
        default="x>=1", description="Post-transform: True if at least one match."
    )


class Insurance(TableBlock[InsuranceParams]):
    config = BlockConfig(
        output_type=OutputType.CATEGORY,
        block_type="event",
        date_column=("patient_insurance_start_date", "patient_insurance_end_date"),
        description="Retourne les différentes couvertures d'assurance du patient.",
    )

    def transform(self, patient_insurance: pl.DataFrame) -> pl.DataFrame:  # type: ignore[override]
        insurance_type_label = self.params.value
        return patient_insurance.filter(
            pl.col("patient_insurance_type_label").is_in(insurance_type_label)
        ).select(
            "patient_id",
            pl.col("patient_insurance_type_label").alias(self.name),
            self.start_date_column,
            self.end_date_column,
        )
