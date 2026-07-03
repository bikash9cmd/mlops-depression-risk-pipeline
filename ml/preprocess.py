"""
Cleans and merges the base training dataset with freshly logged
predictions, producing a single processed CSV that train.py consumes.
"""

import os
import pandas as pd

RAW_DIR = "/opt/airflow/data/raw"
PROCESSED_DIR = "/opt/airflow/data/processed"
BASE_FILE = os.path.join(RAW_DIR, "depression_survey.csv")
LOGGED_FILE = os.path.join(RAW_DIR, "logged_predictions.csv")
OUTPUT_FILE = os.path.join(PROCESSED_DIR, "training_data.csv")

FEATURE_COLUMNS = [
    "age",
    "sleep_hours",
    "work_hours",
    "academic_pressure",
    "financial_stress",
    "social_support",
]
TARGET_COLUMN = "risk_label"


def load_and_clean(path):
    df = pd.read_csv(path)
    df = df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    df = df[(df["age"] >= 10) & (df["age"] <= 100)]
    df = df[(df["sleep_hours"] >= 0) & (df["sleep_hours"] <= 24)]
    return df


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    frames = []
    if os.path.exists(BASE_FILE):
        frames.append(load_and_clean(BASE_FILE))
    if os.path.exists(LOGGED_FILE):
        frames.append(load_and_clean(LOGGED_FILE))

    if not frames:
        raise FileNotFoundError("No source data found in data/raw/")

    combined = pd.concat(frames, ignore_index=True).drop_duplicates()
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"Processed dataset written to {OUTPUT_FILE} ({len(combined)} rows)")


if __name__ == "__main__":
    main()
