import os
from collections import defaultdict
from pathlib import Path

import polars as pl

from requipso.io import S3IO, BaseIO, LocalIO


class Data:
    def __init__(
        self,
        data_path: Path | str,
        empty: bool = False,
        patient_ids: pl.Series | None = None,
    ):
        self.data_path = data_path
        self.io: BaseIO
        self.patient_ids = patient_ids

        if isinstance(data_path, str) and data_path.startswith("s3://"):
            self.io = S3IO(data_path)
        else:
            self.io = LocalIO(data_path)

        self.data = self.load_data(empty=empty)

        self.results = self.data["patient"].select("patient_id")
        self.all_results = defaultdict(dict)

    def load_data(self, empty: bool = False) -> dict[str, pl.DataFrame]:
        n_rows = 0 if empty else None
        tables = {
            table_name: self.io.read_table(table_name, n_rows=n_rows)
            for table_name in self.io.list_tables()
        }

        if self.patient_ids is not None:
            tables = {
                name: df.filter(pl.col("patient_id").is_in(self.patient_ids))
                if "patient_id" in df.columns
                else df
                for name, df in tables.items()
            }
        return tables

    def __getitem__(self, table_name: str) -> pl.DataFrame:
        return self.data[table_name]

    def __setitem__(self, table_name: str, table: pl.DataFrame) -> None:
        self.data[table_name] = table

    def __getattr__(self, name: str) -> pl.DataFrame:
        if "data" in self.__dict__ and name in self.data:
            return self.data[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __dir__(self) -> list[str]:
        default = list(super().__dir__())
        if "data" in self.__dict__:
            return list(set(default) | set(self.data.keys()))
        return default

    def get_table(self, table_name: str) -> pl.DataFrame:
        return self.data[table_name]

    def set_table(self, table_name: str, table: pl.DataFrame) -> None:
        self.data[table_name] = table

    def reset(self) -> None:
        self.all_results = defaultdict(dict)
        self.results = self.data["patient"].select("patient_id")
