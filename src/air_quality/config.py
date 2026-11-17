"""Project-wide constants: paths, study windows, event dates and city metadata.

Every analytical choice lives here so it is visible, documented and easy to change.
"""

from pathlib import Path

import pandas as pd

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA = PROJECT_ROOT / "data" / "raw" / "city_day.csv"
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed" / "city_day_clean.csv"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
TABLES_DIR = PROJECT_ROOT / "reports" / "tables"

# --- Pollutants --------------------------------------------------------------
POLLUTANTS = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3",
              "Benzene", "Toluene", "Xylene"]
UNITS = {"PM2.5": "µg/m³", "PM10": "µg/m³", "NO2": "µg/m³", "SO2": "µg/m³",
         "O3": "µg/m³", "CO": "mg/m³"}

# --- Data-quality rule -------------------------------------------------------
# A city/pollutant/window combination is only used if at least this share of
# calendar days has a reading. Coverage is measured against calendar days, so
# days with no row at all count as missing.
MIN_COVERAGE = 0.80

# Known sensor problems found during data-quality review (notebook 02).
# Each entry removes values that cannot be trusted, with the reason recorded.
KNOWN_ISSUES = [
    {
        "city": "Ahmedabad",
        "columns": ["CO", "AQI", "AQI_Bucket"],
        "reason": (
            "CO readings run 10-40x above every other city for years, then fall "
            "about 10x within one week in April 2020, consistent with a sensor or "
            "unit-reporting fault. AQI is derived partly from CO, so it is removed too."
        ),
    },
]

# PM2.5 is a subset of PM10, so PM2.5 > PM10 is physically impossible. A 10%
# tolerance allows for normal measurement noise; beyond it, PM2.5 is removed.
PM25_PM10_TOLERANCE = 1.10

# --- Lockdown study ----------------------------------------------------------
# National lockdown phases 1 and 2 (the strictest period).
LOCKDOWN = ("03-25", "05-03")
# Pre-lockdown reference window, ending before the 22 March "Janata curfew".
PRE_LOCKDOWN = ("01-01", "03-21")
STUDY_YEAR = 2020
BASELINE_YEAR = 2019
# If a city's pre-lockdown level changed by more than this between 2019 and 2020,
# the 2019 baseline is not comparable (often a station or sensor change), so the
# city is left out of headline results. It stays in the full results table.
MAX_PRE_TREND = 0.50

# --- Diwali study ------------------------------------------------------------
# Main Diwali (Lakshmi Puja) dates. 2020 is excluded: the dataset ends in July 2020.
DIWALI_DATES = pd.to_datetime([
    "2015-11-11", "2016-10-30", "2017-10-19", "2018-11-07", "2019-10-27",
])
# Days before/after Diwali used as the local baseline. Using both sides cancels
# out the steady seasonal rise in pollution that happens every October-November.
DIWALI_BASELINE_DAYS = [*range(-7, -2), *range(4, 8)]

# --- City metadata -----------------------------------------------------------
REGION = {
    "Delhi": "North", "Gurugram": "North", "Lucknow": "North", "Amritsar": "North",
    "Chandigarh": "North", "Jaipur": "North",
    "Patna": "East", "Kolkata": "East", "Brajrajnagar": "East", "Talcher": "East",
    "Jorapokhar": "East",
    "Guwahati": "Northeast", "Shillong": "Northeast", "Aizawl": "Northeast",
    "Mumbai": "West", "Ahmedabad": "West",
    "Bhopal": "Central",
    "Bengaluru": "South", "Chennai": "South", "Hyderabad": "South",
    "Visakhapatnam": "South", "Amaravati": "South", "Thiruvananthapuram": "South",
    "Kochi": "South", "Ernakulam": "South", "Coimbatore": "South",
}
