from datetime import datetime
from functools import reduce
from sqlite3.dbapi2 import Row
from typing import Any, Generator, Literal, cast, get_args

import gspread  # type: ignore
import pandas as pd
import polars as pl
from gspread_formatting import (  # type: ignore
    CellFormat,
    Color,
    TextFormat,
    format_cell_ranges,
)
from gspread_pandas import Spread  # type: ignore

from requipso.data import Data
from requipso.google import GoogleConnector
from requipso.pipeline import Pipeline
from requipso.pipes.base import BaseBlock
from requipso.stats import (
    compute_stats_boolean,
    compute_stats_categories,
    compute_stats_quantitative,
)

VARIABLE_TYPE = Literal["categorical", "numerical", "boolean"]

RESULTS_SHEET_NAME = "🔒 Results"


class DescriptivePipeline:
    def __init__(
        self,
        data: Data,
        inclusion_pipeline: Pipeline,
        populations: list[str],
        google_connector: GoogleConnector,
    ):

        missing_populations = set(populations) - set(
            inclusion_pipeline.steps_names.keys()
        )
        if missing_populations:
            raise ValueError(
                f"Populations {missing_populations} not found in inclusion pipeline"
            )

        self.inclusion_pipeline = inclusion_pipeline
        self.populations = {
            name: data.all_results[name]["post"]
            .filter(pl.col(name))
            .get_column("patient_id")
            .unique()
            for name in populations
        }
        self.reference_date = inclusion_pipeline.reference_date
        self.rows: list[dict[str, Any]] = []

        self.stats: dict[str, dict[str, pl.DataFrame]] = dict()
        self.stats["Total"] = dict()

        self.patient_ids = pl.concat(self.populations.values()).unique()
        self.google_connector = google_connector

    def add_row(
        self,
        step: BaseBlock,
        variable_type: VARIABLE_TYPE,
        display_name: str | None = None,
        subsets: list[Any] | None = None,
    ) -> None:
        if variable_type not in get_args(VARIABLE_TYPE):
            raise ValueError(f"Variable type {variable_type} not supported")
        if step.name in self.inclusion_pipeline.steps_names:
            raise ValueError(
                f"Step {step.name} already exists in inclusion pipeline, use a different name"
            )
        self.rows.append(
            {
                "step": step,
                "display_name": display_name or step.name,
                "variable_type": variable_type,
                "subsets": subsets,
            }
        )

    def run(self, data: Data) -> pd.DataFrame:
        for _ in self.run_iter(data):
            pass
        df_stats = self.format_stats(self.stats)
        self.upload_stats(df_stats)
        return df_stats

    def run_iter(self, data: Data) -> Generator[dict[str, pl.DataFrame], None, None]:
        main_stats = pl.DataFrame(
            {pop_name: pop.len() for pop_name, pop in self.populations.items()}
        )

        n_general_pop = main_stats.item(0, 0)

        for pop_name in main_stats.columns:
            main_stats = main_stats.with_columns(
                pl.col(pop_name).alias("name"),
                (pl.col(pop_name) / n_general_pop * 100).round(2).alias("pct"),
            ).with_columns(pl.format("{name} ({pct}%)").alias("(n, %)"))

            self.stats["Total"][pop_name] = main_stats.select("(n, %)")

        for row in self.rows:
            step = row["step"]
            variable_type = row["variable_type"]
            subsets = row["subsets"]

            data = step.execute(
                data,
                patient_ids=self.patient_ids,
                reference_date=self.reference_date,
            )

            df: pl.DataFrame = data.all_results[step.name]["post"].select(
                "patient_id",
                pl.col(step.name),
            )
            col = df.get_column(step.name)

            # Check concordance between variable_type and true dtype
            if variable_type == "numerical":
                if not col.dtype.is_numeric():
                    raise ValueError(
                        f"Column {step.name} is not numeric (got {col.dtype}), but variable_type is numerical. Maybe check post_func ?"
                    )
            elif variable_type == "boolean":
                if col.dtype != pl.Boolean:
                    raise ValueError(
                        f"Column {step.name} is not boolean (got {col.dtype}), but variable_type is boolean. Maybe check post_func ?"
                    )

            self.stats[step.name] = dict()
            for population in self.populations:
                self.stats[step.name][population] = self.compute_stats(
                    df.join(
                        self.populations[population].to_frame("patient_id"),
                        on="patient_id",
                        how="inner",
                    ),
                    step.name,
                    subsets,
                    variable_type,
                )

            yield self.stats[step.name]

    def compute_stats(
        self,
        df: pl.DataFrame,
        name: str,
        subsets: list[Any],
        variable_type: VARIABLE_TYPE,
    ) -> pl.DataFrame:
        if variable_type == "categorical":
            return compute_stats_categories(df, name, subsets)
        elif variable_type == "numerical":
            return compute_stats_quantitative(df, name, subsets)
        elif variable_type == "boolean":
            return compute_stats_boolean(df, name)
        else:
            raise ValueError(f"Variable type {variable_type} not supported")

    def format_stats(self, stats: dict[str, dict[str, pl.DataFrame]]) -> pd.DataFrame:
        subtables: list[pl.DataFrame] = []
        for block, pop in stats.items():
            rows = [
                df.transpose(include_header=True, column_names=[pop_name])
                for pop_name, df in pop.items()
            ]

            rows_df = reduce(
                lambda left, right: left.join(
                    right, on="column", how="inner", maintain_order="left"
                ),
                rows,
            )
            header = rows_df.sample(1).select(pl.all().replace(pl.all(), None))
            header[0, "column"] = block
            rows_df = pl.concat([header, rows_df])

            subtables.append(rows_df)

        df = pl.concat(subtables).to_pandas()
        df.columns = [""] + df.columns[1:].tolist()  # type: ignore
        return df

    def upload_stats(self, stats: pd.DataFrame) -> None:

        spread = cast(Spread, self.google_connector.spread)

        # Clear
        sh = spread.spread
        ws = sh.worksheet(RESULTS_SHEET_NAME)

        sheet_id = ws._properties["sheetId"]

        sh.batch_update(
            {
                "requests": [
                    {"updateCells": {"range": {"sheetId": sheet_id}, "fields": "*"}}
                ]
            }
        )

        # Upload
        spread.df_to_sheet(
            stats,
            index=False,
            sheet=RESULTS_SHEET_NAME,
            start="A1",
            replace=True,
        )

        # Format
        ws = spread.spread.worksheet(RESULTS_SHEET_NAME)

        to_format = []

        numbers_fmt = CellFormat(
            textFormat=TextFormat(bold=False), horizontalAlignment="CENTER"
        )
        to_format.append(
            [
                f"A1:{gspread.utils.rowcol_to_a1(len(stats) + 1, len(stats.columns))}",
                numbers_fmt,
            ]
        )

        header_fmt = CellFormat(
            textFormat=TextFormat(bold=True),
            horizontalAlignment="CENTER",
        )
        to_format.append(
            [
                f"A1:{gspread.utils.rowcol_to_a1(1, len(stats.columns))}",
                header_fmt,
            ]
        )

        block_fmt = CellFormat(
            textFormat=TextFormat(bold=True),
            horizontalAlignment="LEFT",
            backgroundColor=Color(159 / 255, 197 / 255, 232 / 255),
        )
        normal_fmt = CellFormat(horizontalAlignment="RIGHT")

        for idx, row in stats.iterrows():
            idx = cast(int, idx)
            if bool(row.drop("").isna().all()):  # Header
                to_format.append(
                    [
                        f"{gspread.utils.rowcol_to_a1(idx + 2, 1)}:{gspread.utils.rowcol_to_a1(idx + 2, len(stats.columns))}",
                        block_fmt,
                    ]
                )
            else:
                to_format.append(
                    [
                        f"{gspread.utils.rowcol_to_a1(idx + 2, 1)}",
                        normal_fmt,
                    ]
                )

        format_cell_ranges(ws, to_format)
