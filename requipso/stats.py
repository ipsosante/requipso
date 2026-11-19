from typing import Any

import numpy as np
import polars as pl


def compute_stats_boolean(
    df: pl.DataFrame,
    name: str,
    n_digits: int = 2,
) -> pl.DataFrame:
    n = df.height
    stats = df.select(
        count=pl.col(name).sum().alias("count"),
        pct=pl.col(name).sum() / n * 100,
        count_missing=(pl.col(name).is_null()).sum().alias("count_missing"),
    ).with_columns(
        pct_missing=pl.col("count_missing") / n * 100,
    )

    stats = stats.select(
        pl.all().round(n_digits),
    )

    stats_formatted = stats.select(
        pl.format("{count} ({pct}%)").alias("(n, %)"),
        pl.format("{count_missing} ({pct_missing}%)").alias("missing (n, %)"),
    )

    return stats_formatted


def compute_stats_categories(
    df: pl.DataFrame,
    name: str,
    subsets: list[Any] | None,
    n_digits: int = 2,
) -> pl.DataFrame:
    data_categories = set(df[name].unique().to_list())

    if subsets is not None:
        subsets = [[cat] if not isinstance(cat, list) else cat for cat in subsets]
    else:
        subsets = [[cat] for cat in data_categories]

    sub_stats = []
    for cat in subsets:
        display = str(cat[0]) if len(cat) == 1 else f"({', '.join(map(str, cat))})"
        df = df.with_columns(pl.col(name).is_in(cat).alias(f"{name}_{cat}"))
        s = compute_stats_boolean(
            df,
            name=f"{name}_{cat}",
            n_digits=n_digits,
        ).select(pl.col("(n, %)").alias(display))
        sub_stats.append(s)

    stats = compute_stats_boolean(
        df.with_columns(pl.lit(True).alias("placeholder")),
        name="placeholder",
        n_digits=n_digits,
    ).select(pl.col("missing (n, %)"))

    return pl.concat(
        [
            stats,
            pl.concat(sub_stats, how="horizontal"),
        ],
        how="horizontal",
    )


def compute_stats_quantitative(
    df: pl.DataFrame,
    name: str,
    subsets: list[Any] | None,
    n_digits: int = 2,
) -> pl.DataFrame:
    sub_stats = []
    n = df.height
    stats = df.select(
        mean=pl.col(name).mean().alias("mean"),
        median=pl.col(name).median().alias("median"),
        std=pl.col(name).std().alias("std"),
        q1=pl.col(name).quantile(0.25).alias("q1"),
        q3=pl.col(name).quantile(0.75).alias("q3"),
        count_missing=(pl.col(name).is_null() | pl.col(name).is_nan())
        .sum()
        .alias("count_missing"),
        pct_missing=(pl.col(name).is_null() | pl.col(name).is_nan()).sum()
        / pl.col("patient_id").len()
        * 100,
    )

    stats = stats.select(
        pl.all().round(n_digits),
    )

    stats_formatted = stats.select(
        pl.format("{mean} ± {std}").alias("(mean ± std)"),
        pl.format("{median} [{q1} - {q3}]").alias("(median, IQR)"),
        pl.format("{count_missing} ({pct_missing}%)").alias("missing (n, %)"),
    )

    if not subsets:
        return stats_formatted

    subsets = subsets + [np.inf]

    for idx in range(len(subsets) - 1):
        low, high = subsets[idx], subsets[idx + 1]
        display = f"[{low} - {high}[" if high != np.inf else f"{low}+"
        mask = (pl.col(name) >= low) & (pl.col(name) < high)
        sub_stats.append(
            df.filter(mask)
            .select(
                count=pl.len().alias("count"),
                pct=(pl.len() / n * 100).round(n_digits).alias("pct"),
            )
            .select(
                pl.format("{count} ({pct}%)").alias(f"{display} (n, %)"),
            )
        )

    return pl.concat(
        [
            stats_formatted,
            pl.concat(sub_stats, how="horizontal"),
        ],
        how="horizontal",
    )
