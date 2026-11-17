"""Estimating the effect of the 2020 lockdown on pollution.

Method
------
For each city we take the median daily concentration in four windows:

    pre-lockdown  (1 Jan - 21 Mar)   in 2019 and 2020
    lockdown      (25 Mar - 3 May)   in 2019 and 2020

* raw change      = lockdown 2020 / lockdown 2019 - 1
* pre-trend       = pre 2020 / pre 2019 - 1
* adjusted change = (lockdown 2020 / lockdown 2019) / (pre 2020 / pre 2019) - 1

The adjusted change removes any difference between 2019 and 2020 that already
existed before the lockdown (weather, new policies, sensor drift). It is a
difference-in-differences on the ratio scale. It still assumes that, without the
lockdown, the 2020-vs-2019 gap would have stayed the same from winter to spring.

Uncertainty comes from a weekly block bootstrap. Days are resampled in 7-day
blocks because pollution on neighbouring days is correlated, so resampling single
days would understate the uncertainty.
"""

import numpy as np
import pandas as pd

from . import config
from .quality import cities_with_coverage, window_dates

WINDOW_KEYS = [
    ("pre", config.BASELINE_YEAR), ("pre", config.STUDY_YEAR),
    ("lockdown", config.BASELINE_YEAR), ("lockdown", config.STUDY_YEAR),
]


def _window(name: str) -> tuple[str, str]:
    return config.LOCKDOWN if name == "lockdown" else config.PRE_LOCKDOWN


def _values(city_df: pd.DataFrame, column: str, name: str, year: int) -> np.ndarray:
    """Daily values for one city in one window, ordered by date, missing days dropped."""
    start, end = window_dates(year, _window(name))
    w = city_df[(city_df["Date"] >= start) & (city_df["Date"] <= end)]
    w = w.dropna(subset=[column])
    # Keep the day offset so bootstrap blocks follow the calendar, not row order.
    offsets = (w["Date"] - start).dt.days.to_numpy()
    return np.column_stack([offsets, w[column].to_numpy(dtype=float)])


STATISTICS = {"median": np.median, "mean": np.mean}


def _block_bootstrap(values: np.ndarray, n_boot: int, rng: np.random.Generator,
                     stat=np.median) -> np.ndarray:
    """Bootstrap distribution of `stat`, resampling whole calendar weeks."""
    weeks = values[:, 0] // 7
    blocks = [values[weeks == w, 1] for w in np.unique(weeks)]
    out = np.empty(n_boot)
    for i in range(n_boot):
        picked = rng.integers(0, len(blocks), size=len(blocks))
        out[i] = stat(np.concatenate([blocks[j] for j in picked]))
    return out


def lockdown_effect(df: pd.DataFrame, column: str, *,
                    min_coverage: float = config.MIN_COVERAGE,
                    max_pre_trend: float = config.MAX_PRE_TREND,
                    statistic: str = "median",
                    n_boot: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Per-city lockdown effect for one pollutant, with 95% bootstrap intervals.

    Only cities meeting `min_coverage` in all four windows are included.
    `stable_baseline` is False when the pre-lockdown 2020-vs-2019 change exceeds
    `max_pre_trend`. `statistic` ("median" or "mean") summarises daily values in
    each window; the median is the default because it is robust to one-off spikes
    such as dust storms or sensor glitches.
    Changes are returned as fractions (-0.30 means a 30% fall).
    """
    stat = STATISTICS[statistic]
    windows = [window_dates(year, _window(name)) for name, year in WINDOW_KEYS]
    cities = cities_with_coverage(df, column, windows, min_coverage)
    rng = np.random.default_rng(seed)

    rows = []
    for city in cities:
        city_df = df[df["City"] == city]
        values = {key: _values(city_df, column, *key) for key in WINDOW_KEYS}
        med = {key: stat(v[:, 1]) for key, v in values.items()}
        boot = {key: _block_bootstrap(v, n_boot, rng, stat) for key, v in values.items()}

        pre19, pre20, lock19, lock20 = (med[k] for k in WINDOW_KEYS)
        if min(pre19, pre20, lock19, lock20) <= 0:
            continue  # a zero median makes every ratio undefined
        b_pre19, b_pre20, b_lock19, b_lock20 = (boot[k] for k in WINDOW_KEYS)
        with np.errstate(divide="ignore", invalid="ignore"):
            adjusted_boot = (b_lock20 / b_lock19) / (b_pre20 / b_pre19) - 1
            adjusted_boot = adjusted_boot[np.isfinite(adjusted_boot)]

        rows.append({
            "City": city,
            "Region": config.REGION.get(city, "Other"),
            "pre_2019": pre19, "pre_2020": pre20,
            "lockdown_2019": lock19, "lockdown_2020": lock20,
            "raw_change": lock20 / lock19 - 1,
            "pre_trend": pre20 / pre19 - 1,
            "adjusted_change": (lock20 / lock19) / (pre20 / pre19) - 1,
            "ci_low": np.percentile(adjusted_boot, 2.5),
            "ci_high": np.percentile(adjusted_boot, 97.5),
            "stable_baseline": abs(pre20 / pre19 - 1) <= max_pre_trend,
        })
    if not rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(rows).sort_values("adjusted_change").reset_index(drop=True)


def _geometric_mean_change(changes: np.ndarray, axis=None) -> np.ndarray:
    """Average of percentage changes on the ratio scale (-50% and +100% cancel out)."""
    return np.expm1(np.mean(np.log1p(changes), axis=axis))


def summarise(effects: pd.DataFrame, *, n_boot: int = 5000, seed: int = 42) -> dict:
    """Change in the typical city (cities with a stable baseline), with a 95% interval.

    "Typical" is the geometric mean of city ratios, the standard way to average
    percentage changes. The interval comes from resampling cities, so it shows how
    much the answer depends on which cities are in the dataset. (A bootstrap of the
    median across only 10-15 cities proved unstable, so the median is reported as a
    secondary figure without an interval.)
    """
    rng = np.random.default_rng(seed)
    if "stable_baseline" in effects:
        effects = effects[effects["stable_baseline"]]
    adjusted = effects["adjusted_change"].to_numpy()
    boot = _geometric_mean_change(rng.choice(adjusted, size=(n_boot, len(adjusted))), axis=1)
    return {
        "n_cities": len(effects),
        "typical_raw_change": float(_geometric_mean_change(effects["raw_change"].to_numpy())),
        "typical_pre_trend": float(_geometric_mean_change(effects["pre_trend"].to_numpy())),
        "typical_adjusted_change": float(_geometric_mean_change(adjusted)),
        "ci_low": float(np.percentile(boot, 2.5)),
        "ci_high": float(np.percentile(boot, 97.5)),
        "median_adjusted_change": float(np.median(adjusted)),
        "cities_clear_decrease": int((effects["ci_high"] < 0).sum()),
        "cities_clear_increase": int((effects["ci_low"] > 0).sum()),
    }


def sensitivity(df: pd.DataFrame, column: str, n_boot: int = 300) -> pd.DataFrame:
    """Headline result under alternative analysis choices, to show how robust it is."""
    scenarios = {
        "Main analysis (median, 80% coverage, ±50% baseline)": {},
        "Mean instead of median": {"statistic": "mean"},
        "Stricter coverage (90%)": {"min_coverage": 0.9},
        "Looser coverage (70%)": {"min_coverage": 0.7},
        "Stricter baseline (±30%)": {"max_pre_trend": 0.3},
        "No baseline filter": {"max_pre_trend": np.inf},
    }
    rows = []
    for name, kwargs in scenarios.items():
        summary = summarise(lockdown_effect(df, column, n_boot=n_boot, **kwargs), n_boot=2000)
        rows.append({"Scenario": name, "Cities": summary["n_cities"],
                     "Simple change": summary["typical_raw_change"],
                     "Adjusted change": summary["typical_adjusted_change"],
                     "95% CI low": summary["ci_low"], "95% CI high": summary["ci_high"]})
    return pd.DataFrame(rows).set_index("Scenario")


def daily_comparison(df: pd.DataFrame, city: str, column: str,
                     rolling_days: int = 7) -> pd.DataFrame:
    """Rolling-mean series for one city, aligned by day of year, for 2019 and 2020."""
    city_df = df[df["City"] == city].set_index("Date")[column]
    out = {}
    for year in (config.BASELINE_YEAR, config.STUDY_YEAR):
        s = city_df[f"{year}-01-01":f"{year}-06-30"]
        s = s.asfreq("D").rolling(rolling_days, min_periods=4, center=True).mean()
        s.index = s.index.day_of_year
        out[year] = s
    return pd.DataFrame(out)
