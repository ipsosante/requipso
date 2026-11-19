import polars as pl
import polars.selectors as cs


# Custom Polars namespace for IPSO-specific processing
@pl.api.register_dataframe_namespace("ipso")
class CustomProcessing:
    def __init__(self, df: pl.DataFrame):
        self._df = df

    def postprocess(self) -> pl.DataFrame:
        """
        Postprocess the DataFrame:
        - Replace empty strings with None
        """
        return self._df.with_columns(cs.string().replace("", None))

    def int_to_uint(self) -> pl.DataFrame:
        return self._df.with_columns(
            pl.col(pl.Int32).cast(pl.UInt32),
            pl.col(pl.Int64).cast(pl.UInt64),
            pl.col(pl.Int8).cast(pl.UInt8),
            pl.col(pl.Int16).cast(pl.UInt16),
        )
