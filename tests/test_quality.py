import pandas as pd
import pytest

from air_quality.quality import cities_with_coverage, coverage
from tests.conftest import daily

START, END = pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-10")


def test_days_without_a_row_count_as_missing():
    # 5 rows for a 10-day window: coverage must be 50%, not 100%.
    df = daily("Delhi", "2020-01-01", "2020-01-05", 1.0)
    assert coverage(df, "PM2.5", START, END)["Delhi"] == pytest.approx(0.5)


def test_nan_values_count_as_missing():
    df = daily("Delhi", "2020-01-01", "2020-01-10", 1.0)
    df.loc[:3, "PM2.5"] = None
    assert coverage(df, "PM2.5", START, END)["Delhi"] == pytest.approx(0.6)


def test_requested_city_with_no_data_has_zero_coverage():
    df = daily("Delhi", "2020-01-01", "2020-01-10", 1.0)
    assert coverage(df, "PM2.5", START, END, cities=["Delhi", "Mumbai"])["Mumbai"] == 0


def test_city_must_meet_threshold_in_every_window():
    df = pd.concat([
        daily("Delhi", "2019-01-01", "2020-01-10", 1.0),
        daily("Mumbai", "2020-01-01", "2020-01-10", 1.0),  # no 2019 data
    ])
    windows = [(pd.Timestamp("2019-01-01"), pd.Timestamp("2019-01-10")), (START, END)]
    assert cities_with_coverage(df, "PM2.5", windows, 0.8) == ["Delhi"]
