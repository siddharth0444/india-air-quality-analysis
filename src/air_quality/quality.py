"""Data-coverage measurement.

Coverage is always measured against *calendar days*. A city with no row at all for
a day is missing that day, which a simple `isna()` on the existing rows would miss.
"""

import pandas as pd


def window_dates(year: int, window: tuple[str, str]) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Turn a ("MM-DD", "MM-DD") window into start and end timestamps for a year."""
    start, end = window
    return pd.Timestamp(f"{year}-{start}"), pd.Timestamp(f"{year}-{end}")


def coverage(df: pd.DataFrame, column: str, start: pd.Timestamp, end: pd.Timestamp,
             cities: list[str] | None = None) -> pd.Series:
    """Share of calendar days in [start, end] with a non-missing value, per city."""
    cities = sorted(df["City"].unique()) if cities is None else cities
    n_days = (end - start).days + 1
    in_window = df[(df["Date"] >= start) & (df["Date"] <= end)]
    observed = in_window.groupby("City")[column].count()
    return (observed.reindex(cities, fill_value=0) / n_days).rename(column)


def coverage_by_year(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """City x year table of coverage for one pollutant (0 to 1)."""
    years = range(df["Date"].dt.year.min(), df["Date"].dt.year.max() + 1)
    table = {}
    for year in years:
        start = pd.Timestamp(f"{year}-01-01")
        end = min(pd.Timestamp(f"{year}-12-31"), df["Date"].max())
        table[year] = coverage(df, column, start, end)
    return pd.DataFrame(table)


def cities_with_coverage(df: pd.DataFrame, column: str,
                         windows: list[tuple[pd.Timestamp, pd.Timestamp]],
                         min_coverage: float) -> list[str]:
    """Cities meeting the coverage threshold in *every* given window."""
    per_window = pd.concat(
        [coverage(df, column, start, end) for start, end in windows], axis=1
    )
    return sorted(per_window.index[(per_window >= min_coverage).all(axis=1)])
