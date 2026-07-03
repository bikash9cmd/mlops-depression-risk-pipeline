"""
Compares the most recent processed dataset against a stored reference
sample using Evidently AI, writes an HTML drift report, and logs a
summary row into the drift_reports table so Grafana can chart drift
frequency over time.
"""

import os
import json
import pandas as pd
import sqlalchemy
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

REFERENCE_PATH = "/opt/airflow/data/processed/reference_data.csv"
CURRENT_PATH = "/opt/airflow/data/processed/training_data.csv"
REPORT_DIR = "/opt/airflow/data/drift_reports"

DB_URL = "mysql+pymysql://{user}:{pwd}@{host}:3306/{db}".format(
    user=os.getenv("MARIADB_USER", "airflow"),
    pwd=os.getenv("MARIADB_PASSWORD", "airflow"),
    host=os.getenv("MARIADB_HOST", "mariadb"),
    db=os.getenv("MARIADB_DATABASE", "depression_pipeline"),
)


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    current = pd.read_csv(CURRENT_PATH)

    if not os.path.exists(REFERENCE_PATH):
        # First run: bootstrap the reference set from the current data
        current.to_csv(REFERENCE_PATH, index=False)
        print("No reference dataset found - bootstrapped one, skipping drift check.")
        return

    reference = pd.read_csv(REFERENCE_PATH)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)

    from datetime import datetime

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"drift_report_{timestamp}.html")
    report.save_html(report_path)

    result = report.as_dict()
    dataset_drift = result["metrics"][0]["result"]["dataset_drift"]
    drifted_columns = result["metrics"][0]["result"]["number_of_drifted_columns"]

    engine = sqlalchemy.create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO drift_reports (report_path, dataset_drift, drifted_columns)
                VALUES (:path, :drift, :cols)
                """
            ),
            {"path": report_path, "drift": bool(dataset_drift), "cols": drifted_columns},
        )

    print(f"Drift report saved to {report_path} | dataset_drift={dataset_drift}")


if __name__ == "__main__":
    main()
