"""Download the 'Air Quality Data in India (2015-2020)' dataset into data/raw/.

Source: https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india

Usage (from the project root):
    python scripts/download_data.py
"""

import shutil
from pathlib import Path

import kagglehub

DATASET = "rohanrao/air-quality-data-in-india"
FILES = ["city_day.csv", "stations.csv"]
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    download_dir = Path(kagglehub.dataset_download(DATASET))

    for name in FILES:
        source = download_dir / name
        if not source.exists():
            raise FileNotFoundError(f"{name} not found in {download_dir}")
        shutil.copy2(source, RAW_DIR / name)
        print(f"Saved {RAW_DIR / name}")


if __name__ == "__main__":
    main()
