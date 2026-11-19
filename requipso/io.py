import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar
from urllib.parse import urlparse

import boto3
import polars as pl

T = TypeVar("T", Path, str)


class BaseIO(ABC, Generic[T]):
    data_path: T

    def __init__(self, data_path: T):
        self.data_path = data_path

    @abstractmethod
    def path_from_table_name(self, table_name: str) -> T:
        """Get the full path for a given table name."""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Return a list of available table identifiers."""

    @abstractmethod
    def read_table(self, table_name: str, n_rows: int | None = None) -> pl.DataFrame:
        """Load a parquet table into a Polars DataFrame."""

    @abstractmethod
    def write_table(self, table_name: str, table: pl.DataFrame) -> None:
        """Write a Polars DataFrame to a parquet table."""


class LocalIO(BaseIO[Path]):
    def __init__(self, data_path: Path | str):
        super().__init__(Path(data_path))

    def path_from_table_name(self, table_name: str) -> Path:
        return self.data_path / f"{table_name}.parquet"

    def list_tables(self) -> list[str]:
        return [p.stem for p in self.data_path.glob("*.parquet")]

    def read_table(self, table_name: str, n_rows: int | None = None) -> pl.DataFrame:
        table_path = self.path_from_table_name(table_name)
        if not table_path.exists():
            raise FileNotFoundError(f"Table {table_name} not found at {table_path}")
        return pl.read_parquet(table_path, n_rows=n_rows)

    def write_table(self, table_name: str, table: pl.DataFrame) -> None:
        table_path = self.path_from_table_name(table_name)
        table.write_parquet(table_path)


class S3IO(BaseIO[str]):
    def __init__(self, data_path: str):
        super().__init__(data_path.strip("/"))

        self.s3 = boto3.client("s3")

        if not self.data_path.startswith("s3://"):
            raise ValueError("data_path must be an s3 URI like s3://bucket/prefix")

        if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
            raise EnvironmentError("AWS credentials not found in environment variables")

        parsed = urlparse(self.data_path)
        if parsed.scheme != "s3" or not parsed.netloc:
            raise ValueError("data_path must be an s3 URI like s3://bucket/prefix")

        self.bucket_name = parsed.netloc
        self.prefix = parsed.path.lstrip("/")

    def path_from_table_name(self, table_name: str) -> str:
        if self.prefix:
            return f"s3://{self.bucket_name}/{self.prefix}/{table_name}.parquet"
        else:
            return f"s3://{self.bucket_name}/{table_name}.parquet"

    def list_tables(self) -> list[str]:
        response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=self.prefix)
        return [
            obj["Key"].split(".parquet")[0]
            for obj in response.get("Contents", [])
            if obj["Key"].endswith(".parquet")
        ]

    def read_table(self, table_name: str, n_rows: int | None = None) -> pl.DataFrame:
        return pl.read_parquet(self.path_from_table_name(table_name), n_rows=n_rows)

    def write_table(self, table_name: str, table: pl.DataFrame) -> None:
        table_path = self.path_from_table_name(table_name)
        table.write_parquet(table_path)
