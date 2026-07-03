"""
Runs as a long-lived sidecar container. Every 6 hours it regenerates an
HTML data-drift report comparing the reference training sample against
the latest batch of served predictions, and drops it into ./reports so
it can be linked from Grafana or opened directly.

This is separate from the one-off drift_check.py invoked by the Airflow
DAG - that one gates model promotion, this one is for continuous
visibility even between retraining runs.
"""

import os
import time
import schedule
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

DATA_DIR = "/app/data"
REFERENCE_PATH = os.path.join(DATA_DIR, "processed", "reference_data.csv")
CURRENT_PATH = os.path.join(DATA_DIR, "processed", "training_data.csv")
REPORT_DIR = "/app/reports"


def build_report():
    if not (os.path.exists(REFERENCE_PATH) and os.path.exists(CURRENT_PATH)):
        print("Reference or current dataset not yet available, skipping.")
        return

    reference = pd.read_csv(REFERENCE_PATH)
    current = pd.read_csv(CURRENT_PATH)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)

    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(REPORT_DIR, "latest_drift_report.html")
    report.save_html(out_path)
    print(f"Refreshed drift report at {out_path}")


if __name__ == "__main__":
    build_report()
    schedule.every(6).hours.do(build_report)
    while True:
        schedule.run_pending()
        time.sleep(60)
