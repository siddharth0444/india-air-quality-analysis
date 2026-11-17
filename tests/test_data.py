import pandas as pd
import pytest

from air_quality.data import (
    add_calendar_columns,
    apply_known_issues,
    remove_impossible_pm25,
    validate,
)


def test_validate_accepts_clean_table(full_frame):
    validate(full_frame)


def test_validate_rejects_missing_columns(full_frame):
    with pytest.raises(ValueError, match="Missing columns"):
        validate(full_frame.drop(columns=["NO2"]))


def test_validate_rejects_duplicate_city_days(full_frame):
    with pytest.raises(ValueError, match="duplicate"):
        validate(pd.concat([full_frame, full_frame.head(1)]))


def test_validate_rejects_negative_values(full_frame):
    full_frame.loc[0, "PM2.5"] = -1
    with pytest.raises(ValueError, match="negative"):
        validate(full_frame)


def test_known_issues_only_blank_the_listed_city_and_columns(full_frame):
    other = full_frame.assign(City="Mumbai")
    df = pd.concat([full_frame, other], ignore_index=True)
    issues = [{"city": "Delhi", "columns": ["CO", "AQI"], "reason": "test"}]

    out = apply_known_issues(df, issues)

    delhi, mumbai = out[out.City == "Delhi"], out[out.City == "Mumbai"]
    assert delhi[["CO", "AQI"]].isna().all().all()
    assert delhi["PM2.5"].notna().all()
    assert mumbai[["CO", "AQI"]].notna().all().all()
    assert df["CO"].notna().all(), "input DataFrame must not be modified"


def test_pm25_above_pm10_is_removed_only_beyond_tolerance(full_frame):
    df = full_frame.head(4).copy()
    df["PM10"] = [100.0, 100.0, 100.0, None]
    df["PM2.5"] = [60.0, 105.0, 150.0, 900.0]  # fine, within noise, impossible, unverifiable

    out = remove_impossible_pm25(df, tolerance=1.1)

    assert out["PM2.5"].tolist()[:2] == [60.0, 105.0]
    assert pd.isna(out["PM2.5"].iloc[2])
    assert out["PM2.5"].iloc[3] == 900.0, "can't check without PM10, so keep it"


def test_calendar_columns(full_frame):
    out = add_calendar_columns(full_frame)
    assert out.loc[0, ["Year", "Month", "Region"]].tolist() == [2019, 1, "North"]
