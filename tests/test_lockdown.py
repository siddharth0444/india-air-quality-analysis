import numpy as np
import pandas as pd
import pytest

from air_quality.lockdown import lockdown_effect, summarise
from tests.conftest import daily


def city_with_known_effect(city: str, pre_2020: float, lockdown_2020: float) -> pd.DataFrame:
    """2019 is flat at 100; 2020 is `pre_2020` before 22 March and `lockdown_2020` after."""
    def value_2020(d):
        return pre_2020 if d < pd.Timestamp("2020-03-22") else lockdown_2020
    return pd.concat([
        daily(city, "2019-01-01", "2019-06-30", 100.0),
        daily(city, "2020-01-01", "2020-06-30", value_2020),
    ])


def test_adjusted_change_removes_the_pre_existing_gap():
    # 2020 was already 20% cleaner before lockdown, and 60% cleaner during it.
    # Adjusted effect: 0.4 / 0.8 - 1 = -50%.
    effects = lockdown_effect(city_with_known_effect("Delhi", 80, 40), "PM2.5", n_boot=200)
    row = effects.iloc[0]
    assert row["raw_change"] == pytest.approx(-0.6)
    assert row["pre_trend"] == pytest.approx(-0.2)
    assert row["adjusted_change"] == pytest.approx(-0.5)
    assert row["ci_low"] == pytest.approx(-0.5) and row["ci_high"] == pytest.approx(-0.5)


def test_no_lockdown_effect_gives_zero_even_if_years_differ():
    effects = lockdown_effect(city_with_known_effect("Delhi", 70, 70), "PM2.5", n_boot=200)
    assert effects.iloc[0]["raw_change"] == pytest.approx(-0.3)
    assert effects.iloc[0]["adjusted_change"] == pytest.approx(0.0)


def test_cities_with_poor_coverage_are_excluded():
    sparse = city_with_known_effect("Mumbai", 80, 40)
    sparse = sparse[sparse["Date"].dt.day % 2 == 0]  # about half the days
    df = pd.concat([city_with_known_effect("Delhi", 80, 40), sparse])
    assert lockdown_effect(df, "PM2.5", n_boot=50)["City"].tolist() == ["Delhi"]


def test_bootstrap_interval_contains_estimate_for_noisy_data():
    rng = np.random.default_rng(0)
    df = city_with_known_effect("Delhi", 80, 40)
    df["PM2.5"] = df["PM2.5"] * rng.lognormal(0, 0.2, len(df))
    row = lockdown_effect(df, "PM2.5", n_boot=500).iloc[0]
    assert row["ci_low"] < row["adjusted_change"] < row["ci_high"]
    assert row["ci_high"] < 0


def test_unstable_baseline_is_flagged_and_left_out_of_summary():
    # Delhi: 2020 pre-lockdown level 3x the 2019 level, so the baseline is not comparable.
    df = pd.concat([
        city_with_known_effect("Delhi", 300, 150),
        city_with_known_effect("Mumbai", 80, 40),
    ])
    effects = lockdown_effect(df, "PM2.5", n_boot=50).set_index("City")
    assert not effects.loc["Delhi", "stable_baseline"]
    assert effects.loc["Mumbai", "stable_baseline"]
    summary = summarise(effects.reset_index(), n_boot=50)
    assert summary["n_cities"] == 1
    assert summary["typical_adjusted_change"] == pytest.approx(-0.5)


def test_city_with_zero_median_is_skipped():
    df = city_with_known_effect("Delhi", 0, 0)
    assert lockdown_effect(df, "PM2.5", n_boot=50).empty


def test_summary_averages_changes_on_the_ratio_scale():
    # Halving in one city and doubling in another should average to no change.
    effects = pd.DataFrame({
        "adjusted_change": [-0.5, 1.0], "raw_change": [-0.5, 1.0], "pre_trend": [0.0, 0.0],
        "ci_low": [-0.6, 0.8], "ci_high": [-0.4, 1.2],
    })
    summary = summarise(effects, n_boot=500)
    assert summary["typical_adjusted_change"] == pytest.approx(0.0, abs=1e-12)
    assert summary["cities_clear_decrease"] == 1
    assert summary["cities_clear_increase"] == 1


def test_summary_interval_contains_typical_change():
    effects = pd.DataFrame({
        "adjusted_change": [-0.5, -0.3, -0.1], "raw_change": [-0.6, -0.4, -0.2],
        "pre_trend": [0.0, 0.0, 0.0], "ci_low": [-0.6, -0.4, -0.2], "ci_high": [-0.4, -0.2, 0.05],
    })
    summary = summarise(effects, n_boot=500)
    expected = (0.5 * 0.7 * 0.9) ** (1 / 3) - 1
    assert summary["typical_adjusted_change"] == pytest.approx(expected)
    assert summary["ci_low"] <= expected <= summary["ci_high"]
