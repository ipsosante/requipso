import polars as pl

from requipso import RESOURCES_DIR

def get_mapping() -> pl.DataFrame:
    path = RESOURCES_DIR / "pathology" / "mapping.parquet"
    return pl.read_parquet(path)