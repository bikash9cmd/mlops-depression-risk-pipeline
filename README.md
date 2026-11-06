# MLOps Depression Risk Pipeline

> **Tech stack:** Python · Apache Airflow · FastAPI · Redis · MariaDB · Docker Compose

A multi-container MLOps stack for predicting depression risk from
lifestyle/survey inputs, built as part of BCU CMP5366. The project
covers the full lifecycle: scheduled retraining, a REST inference
service, data drift monitoring, and metrics/dashboards - all wired
together with Docker Compose and managed on the host via `systemctl`.

## Stack

| Component   | Role                                                        |
|-------------|-------------------------------------------------------------|
| Airflow     | Orchestrates daily retraining, drift checks, model promotion |
| FastAPI     | Serves `/predict` REST endpoint, exposes Prometheus metrics |
| Redis       | Caches recent prediction results                             |
| MariaDB     | Stores prediction logs, model registry, drift report history |
| Evidently AI| Generates data drift HTML reports                            |
| Prometheus  | Scrapes API metrics                                           |
| Grafana     | Dashboards for request volume, latency, risk distribution     |

## Architecture

```
                     ┌─────────────┐
                     │   Airflow   │  daily DAG: extract → preprocess
                     │ (scheduler, │  → train → drift check → promote
                     │  webserver) │
                     └──────┬──────┘
                            │ writes model + reads/writes DB
                            ▼
┌────────┐   REST   ┌─────────────┐        ┌────────────┐
│ Client │ ───────▶ │  FastAPI    │ ─────▶ │  MariaDB   │
└────────┘          │  /predict   │        │ predictions│
                     └──────┬──────┘        │ registry   │
                            │ cache          └────────────┘
                            ▼
                     ┌─────────────┐
                     │    Redis    │
                     └─────────────┘

FastAPI /metrics ──▶ Prometheus ──▶ Grafana dashboards
Evidently sidecar ──▶ periodic drift HTML reports
```

## Getting started

```bash
git clone <this-repo>
cd mlops-depression-risk-pipeline
cp .env.example .env        # fill in real passwords
mkdir -p data/raw
# drop your depression_survey.csv into data/raw/ (see data/raw/README.md)

docker compose up -d --build
```

Once everything is up:

- API docs: http://localhost:8000/docs
- Airflow UI: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (default creds from `.env`)

Trigger the `depression_risk_pipeline` DAG manually the first time to
train an initial model, since the API container will otherwise start
with no model loaded.

## Running as a systemd service

For a persistent Linux server deployment rather than manually running
`docker compose up`:

```bash
sudo cp systemd/mlops-stack.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mlops-stack
sudo systemctl status mlops-stack
```

`systemd/deploy.sh` handles pulling new code, rebuilding images, and
restarting the service in one step - useful for a simple CI/CD hook.

`systemd/healthcheck.sh` runs a quick smoke test against every
component and returns a non-zero exit code if anything is down; good
for wiring into a systemd timer or cron job with alerting.

## Operational scripts

| Script                        | Purpose                                     |
|--------------------------------|----------------------------------------------|
| `scripts/backup_db.sh`         | Nightly MariaDB dump with 14-day retention   |
| `scripts/restart_services.sh`  | Restart one, several, or all containers      |
| `scripts/logs.sh`              | Tail logs for one service or the whole stack |

## Retraining pipeline

The Airflow DAG (`airflow/dags/depression_pipeline_dag.py`) runs daily:

1. **extract_prediction_logs** - pulls the last day of served
   predictions out of MariaDB so the model can learn from real traffic.
2. **preprocess_dataset** - cleans and merges with the base training set.
3. **train_model** - fits a `GradientBoostingClassifier`, logs metrics
   to `model_registry`.
4. **check_data_drift** - runs Evidently's `DataDriftPreset` against a
   stored reference sample; fails the DAG run if the check itself errors.
5. **promote_model_if_better** - only swaps in the new model if its F1
   score beats the currently active one.

## Monitoring

- `monitoring/evidently/generate_report.py` runs continuously as its
  own container, refreshing a drift report every 6 hours independent
  of the retraining schedule.
- `monitoring/prometheus/prometheus.yml` scrapes `/metrics` on the API
  every 15s.
- `monitoring/grafana/dashboards/mlops_dashboard.json` is auto-provisioned
  and shows request rate, p95 latency, and the high/low risk split.

## Notes

- All service credentials are pulled from `.env` - never commit that
  file (see `.gitignore`).
- `db/init.sql` runs automatically on the first MariaDB container start
  and creates the schema described above.
- The model file swapped in by `promote.py` is picked up by FastAPI on
  next restart; add a file-watcher or a `/reload` endpoint if you want
  hot-swapping without a restart.
