"""Loading, validating and cleaning the city-day dataset."""

from pathlib import Path

import pandas as pd

from . import config

REQUIRED_COLUMNS = ["City", "Date", *config.POLLUTANTS, "AQI", "AQI_Bucket"]


def load_raw(path: Path = config.RAW_DATA) -> pd.DataFrame:
    """Read the raw CSV, parse dates and check the table has the expected shape."""
    if not Path(path).exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python scripts/download_data.py` first."
        )
    df = pd.read_csv(path, parse_dates=["Date"])
    validate(df)
    return df.sort_values(["City", "Date"]).reset_index(drop=True)


def validate(df: pd.DataFrame) -> None:
    """Raise ValueError if the table breaks any assumption the analysis relies on."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if df.duplicated(["City", "Date"]).any():
        raise ValueError("Found duplicate City/Date rows; expected one row per city per day.")
    numeric = df[[*config.POLLUTANTS, "AQI"]]
    if (numeric < 0).any().any():
        raise ValueError("Found negative concentrations, which are physically impossible.")


def apply_known_issues(df: pd.DataFrame, issues: list[dict] = config.KNOWN_ISSUES) -> pd.DataFrame:
    """Blank out values listed in config.KNOWN_ISSUES. Returns a new DataFrame."""
    out = df.copy()
    for issue in issues:
        rows = out["City"] == issue["city"]
        out.loc[rows, issue["columns"]] = pd.NA
    return out


def remove_impossible_pm25(df: pd.DataFrame,
                           tolerance: float = config.PM25_PM10_TOLERANCE) -> pd.DataFrame:
    """Blank PM2.5 where it exceeds PM10 by more than `tolerance` (PM2.5 is part of PM10)."""
    out = df.copy()
    impossible = out["PM2.5"] > out["PM10"] * tolerance  # False wherever either is missing
    out.loc[impossible, "PM2.5"] = pd.NA
    return out


def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add year, month and region columns used throughout the analysis."""
    out = df.copy()
    out["Year"] = out["Date"].dt.year
    out["Month"] = out["Date"].dt.month
    out["Region"] = out["City"].map(config.REGION).fillna("Other")
    return out


def load_clean(path: Path = config.RAW_DATA) -> pd.DataFrame:
    """Full cleaning pipeline: load, validate, remove untrustworthy values, add calendar columns."""
    return add_calendar_columns(remove_impossible_pm25(apply_known_issues(load_raw(path))))
