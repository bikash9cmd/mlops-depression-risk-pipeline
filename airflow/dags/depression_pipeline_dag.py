"""
depression_pipeline_dag.py

Orchestrates the end-to-end retraining pipeline for the depression risk model:
  1. pull fresh prediction logs from MariaDB
  2. preprocess / merge with training set
  3. retrain the model
  4. run an Evidently AI drift check against the previous reference set
  5. push a fresh reference dataset if no significant drift is found

Scheduled daily, but can be triggered manually from the Airflow UI as well.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "bikash",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="depression_risk_pipeline",
    default_args=default_args,
    description="Retrain and monitor the depression risk model",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mlops", "depression-risk", "cmp5366"],
) as dag:

    extract_logs = BashOperator(
        task_id="extract_prediction_logs",
        bash_command="python /opt/airflow/ml/extract_logs.py",
    )

    preprocess = BashOperator(
        task_id="preprocess_dataset",
        bash_command="python /opt/airflow/ml/preprocess.py",
    )

    train_model = BashOperator(
        task_id="train_model",
        bash_command="python /opt/airflow/ml/train.py",
    )

    def run_drift_check(**_):
        import subprocess

        result = subprocess.run(
            ["python", "/opt/airflow/ml/drift_check.py"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"Drift check failed: {result.stderr}")

    check_drift = PythonOperator(
        task_id="check_data_drift",
        python_callable=run_drift_check,
    )

    promote_model = BashOperator(
        task_id="promote_model_if_better",
        bash_command="python /opt/airflow/ml/promote.py",
    )

    extract_logs >> preprocess >> train_model >> check_drift >> promote_model
