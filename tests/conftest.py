import numpy as np
import pandas as pd
import pytest

from air_quality import config


def daily(city: str, start: str, end: str, values, column: str = "PM2.5") -> pd.DataFrame:
    """One row per day for a city; `values` may be a scalar, an array or a function of date."""
    dates = pd.date_range(start, end, freq="D")
    if callable(values):
        values = [values(d) for d in dates]
    return pd.DataFrame({"City": city, "Date": dates, column: np.broadcast_to(values, len(dates))})


@pytest.fixture
def full_frame():
    """Minimal valid raw table with every required column."""
    df = daily("Delhi", "2019-01-01", "2019-01-10", 50.0)
    for col in [*config.POLLUTANTS, "AQI"]:
        df[col] = 10.0
    df["AQI_Bucket"] = "Moderate"
    return df
