"""
Trains a gradient-boosted classifier on the processed dataset and
registers the resulting model + metrics into MariaDB's model_registry
table. The model itself is written to /opt/airflow/models so the
FastAPI service (mounted on the same host volume) can pick it up.
"""

import os
import json
import joblib
import pandas as pd
import sqlalchemy
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, roc_auc_score

DATA_PATH = "/opt/airflow/data/processed/training_data.csv"
MODEL_DIR = "/opt/airflow/models"
FEATURE_COLUMNS = [
    "age",
    "sleep_hours",
    "work_hours",
    "academic_pressure",
    "financial_stress",
    "social_support",
]
TARGET_COLUMN = "risk_label"

DB_URL = "mysql+pymysql://{user}:{pwd}@{host}:3306/{db}".format(
    user=os.getenv("MARIADB_USER", "airflow"),
    pwd=os.getenv("MARIADB_PASSWORD", "airflow"),
    host=os.getenv("MARIADB_HOST", "mariadb"),
    db=os.getenv("MARIADB_DATABASE", "depression_pipeline"),
)


def main():
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "clf",
                GradientBoostingClassifier(
                    n_estimators=200,
                    max_depth=3,
                    learning_rate=0.05,
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)[:, 1]
    f1 = f1_score(y_test, preds, average="weighted")
    try:
        auc = roc_auc_score(y_test, probs)
    except ValueError:
        auc = None

    version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, f"depression_risk_model_{version}.pkl")
    joblib.dump(pipeline, model_path)

    metadata = {
        "version": version,
        "f1_score": f1,
        "roc_auc": auc,
        "rows": len(df),
        "model_path": model_path,
    }
    with open(os.path.join(MODEL_DIR, "latest_metadata.json"), "w") as fh:
        json.dump(metadata, fh, indent=2)

    engine = sqlalchemy.create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO model_registry (model_version, training_rows, f1_score, roc_auc, is_active)
                VALUES (:version, :rows, :f1, :auc, FALSE)
                """
            ),
            {"version": version, "rows": len(df), "f1": f1, "auc": auc},
        )

    print(f"Trained model {version} | f1={f1:.4f} | auc={auc}")


if __name__ == "__main__":
    main()
