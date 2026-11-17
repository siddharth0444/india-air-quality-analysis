import pandas as pd
import pytest

from air_quality.events import diwali_spike, event_window, monthly_profile, relative_to_baseline
from tests.conftest import daily

DATES = pd.to_datetime(["2017-10-19", "2018-11-07", "2019-10-27"])


def autumn(city: str, year_value) -> pd.DataFrame:
    """Daily data around each test Diwali date, built from `year_value(date)`."""
    frames = [daily(city, d - pd.Timedelta(days=10), d + pd.Timedelta(days=10), year_value)
              for d in DATES]
    return pd.concat(frames, ignore_index=True)


def steady_rise(d: pd.Timestamp) -> float:
    """Pollution rising by 2 units a day, like the October-November build-up."""
    return 100 + 2 * d.day_of_year


def test_seasonal_rise_alone_does_not_look_like_a_diwali_spike():
    rel = relative_to_baseline(event_window(autumn("Delhi", steady_rise), "PM2.5", DATES))
    day0 = rel[rel["day"] == 0]["ratio"]
    assert day0.between(0.98, 1.02).all()


def test_spike_the_day_after_diwali_is_detected():
    diwali_next_day = set(DATES + pd.Timedelta(days=1))

    def value(d):
        return steady_rise(d) * (3 if d in diwali_next_day else 1)

    df = pd.concat([autumn("Delhi", value), autumn("Chennai", steady_rise)])
    result = diwali_spike(df, dates=DATES)
    assert result.loc["Delhi", "peak_day"] == 1
    assert result.loc["Delhi", "peak_ratio"] == pytest.approx(3, rel=0.05)
    assert result.loc["Chennai", "peak_ratio"] == pytest.approx(1, abs=0.03)


def test_cities_with_too_few_diwali_years_are_dropped():
    one_year = daily("Kochi", "2019-10-17", "2019-11-06", steady_rise)
    df = pd.concat([autumn("Delhi", steady_rise), one_year])
    assert diwali_spike(df, dates=DATES, min_years=3).index.tolist() == ["Delhi"]


def test_monthly_profile_skips_cities_missing_months():
    full = daily("Delhi", "2017-01-01", "2019-12-31", 50.0)
    partial = daily("Kochi", "2019-06-01", "2019-12-31", 20.0)
    df = pd.concat([full, partial])
    df["Month"] = df["Date"].dt.month
    profile = monthly_profile(df, min_days_per_month=60)
    assert profile.index.tolist() == ["Delhi"]
