"""Diwali event study and seasonal profiles.

Diwali in North India falls during the post-monsoon season, when pollution is rising
anyway (stubble burning, cooler air trapping pollutants). Comparing Diwali with
"two weeks earlier" would wrongly credit that seasonal rise to the festival.
Instead, each Diwali is compared with a local baseline: the average of days -7..-3
and +4..+7. Days on both sides cancel out a steady seasonal trend.
"""

import numpy as np
import pandas as pd

from . import config


def event_window(df: pd.DataFrame, column: str, dates: pd.DatetimeIndex = config.DIWALI_DATES,
                 before: int = 7, after: int = 7) -> pd.DataFrame:
    """Long table: City, event year, day relative to the event, and the value."""
    frames = []
    for date in dates:
        mask = (df["Date"] >= date - pd.Timedelta(days=before)) & \
               (df["Date"] <= date + pd.Timedelta(days=after))
        w = df.loc[mask, ["City", "Date", column]].copy()
        w["event_year"] = date.year
        w["day"] = (w["Date"] - date).dt.days
        frames.append(w)
    return pd.concat(frames, ignore_index=True).rename(columns={column: "value"})


def relative_to_baseline(events: pd.DataFrame,
                         baseline_days: list[int] = config.DIWALI_BASELINE_DAYS,
                         min_baseline_days: int = 6) -> pd.DataFrame:
    """Divide each value by its city-year local baseline (1.0 = baseline level)."""
    in_base = events[events["day"].isin(baseline_days)]
    stats = in_base.groupby(["City", "event_year"])["value"].agg(["mean", "count"])
    stats = stats[stats["count"] >= min_baseline_days]["mean"].rename("baseline")
    out = events.join(stats, on=["City", "event_year"], how="inner")
    out["ratio"] = out["value"] / out["baseline"]
    return out


def diwali_spike(df: pd.DataFrame, column: str = "PM2.5", min_years: int = 3,
                 dates: pd.DatetimeIndex = config.DIWALI_DATES) -> pd.DataFrame:
    """Per-city typical (median across years) ratio to baseline for days -3..+3.

    Also reports the peak day and the number of Diwali years with usable data.
    """
    rel = relative_to_baseline(event_window(df, column, dates))
    by_day = rel.groupby(["City", "day"])["ratio"].median().unstack("day")
    years = rel.groupby("City")["event_year"].nunique()
    by_day = by_day[years.reindex(by_day.index) >= min_years]

    near = by_day.loc[:, -3:3]
    result = pd.DataFrame({
        "Region": [config.REGION.get(c, "Other") for c in near.index],
        "years": years.reindex(near.index).to_numpy(),
        "peak_day": near.idxmax(axis=1).astype(int),
        "peak_ratio": near.max(axis=1),
        "day_before": by_day[-1], "diwali_day": by_day[0], "day_after": by_day[1],
    }, index=near.index)
    return result.sort_values("peak_ratio", ascending=False)


def event_profile(df: pd.DataFrame, cities: list[str], column: str = "PM2.5",
                  dates: pd.DatetimeIndex = config.DIWALI_DATES) -> pd.DataFrame:
    """Median ratio-to-baseline by day for a group of cities (rows: day, columns: city)."""
    rel = relative_to_baseline(event_window(df[df["City"].isin(cities)], column, dates))
    return rel.groupby(["day", "City"])["ratio"].median().unstack("City")


def monthly_profile(df: pd.DataFrame, column: str = "PM2.5",
                    min_days_per_month: int = 60) -> pd.DataFrame:
    """City x month median concentration, pooled across all years.

    Cities need at least `min_days_per_month` readings in every month to appear,
    so a city is not judged on one unusual year.
    """
    counts = df.groupby(["City", "Month"])[column].count().unstack("Month")
    medians = df.groupby(["City", "Month"])[column].median().unstack("Month")
    keep = (counts >= min_days_per_month).all(axis=1)
    medians = medians[keep.reindex(medians.index, fill_value=False)]
    order = medians.mean(axis=1).sort_values(ascending=False).index
    return medians.loc[order]


def seasonal_swing(profile: pd.DataFrame) -> pd.Series:
    """Worst month divided by best month, per city."""
    return (profile.max(axis=1) / profile.min(axis=1)).replace([np.inf], np.nan)
