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

# Same bounds the API enforces in api/app/schemas.py, so the model is
# never trained on rows that /predict would reject with a 422.
FEATURE_BOUNDS = {
    "age": (10, 100),
    "sleep_hours": (0, 24),
    "work_hours": (0, 24),
    "academic_pressure": (0, 10),
    "financial_stress": (0, 10),
    "social_support": (0, 10),
}

# The base survey stores the target as 0/1, while logged predictions
# carry the API's string labels. Both map onto the same binary target.
LABEL_MAP = {
    "0": 0,
    "1": 1,
    "low_risk": 0,
    "high_risk": 1,
}


def normalize_labels(labels):
    """Map raw risk labels onto 0/1. Unrecognised values become NA."""

    def _to_key(value):
        if pd.isna(value):
            return None
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value).strip().lower()

    return labels.map(lambda v: LABEL_MAP.get(_to_key(v))).astype("Int64")


def load_and_clean(path):
    df = pd.read_csv(path)
    df = df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    for column in FEATURE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=FEATURE_COLUMNS)
    for column, (low, high) in FEATURE_BOUNDS.items():
        df = df[(df[column] >= low) & (df[column] <= high)]

    df[TARGET_COLUMN] = normalize_labels(df[TARGET_COLUMN])
    unknown = int(df[TARGET_COLUMN].isna().sum())
    if unknown:
        print(f"Dropping {unknown} rows from {path} with an unrecognised {TARGET_COLUMN}")
    df = df.dropna(subset=[TARGET_COLUMN])
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
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
