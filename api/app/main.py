"""
FastAPI service that serves the depression risk model.

Exposes:
  POST /predict        - run inference on a single record
  GET  /health          - liveness/readiness probe
  GET  /metrics          - Prometheus scrape endpoint
  GET  /model/info       - currently loaded model version + metrics

Redis is used to cache recent predictions by a hash of the input so
repeated identical requests (e.g. from a retry) don't hit the model
twice. MariaDB stores every prediction for later retraining/auditing.
"""

import hashlib
import json
import os
import time
import uuid

import joblib
import redis
import sqlalchemy
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .schemas import PredictionRequest, PredictionResponse

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/depression_risk_model.pkl")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
MARIADB_HOST = os.getenv("MARIADB_HOST", "mariadb")
MARIADB_USER = os.getenv("MARIADB_USER", "airflow")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "airflow")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "depression_pipeline")

app = FastAPI(title="Depression Risk Prediction API", version="1.0.0")

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

engine = sqlalchemy.create_engine(
    f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:3306/{MARIADB_DATABASE}"
)

REQUEST_COUNT = Counter(
    "prediction_requests_total", "Total number of prediction requests", ["result"]
)
REQUEST_LATENCY = Histogram(
    "prediction_latency_seconds", "Time taken to serve a prediction"
)

_model = None
_model_version = "unloaded"


def load_model():
    global _model, _model_version
    if os.path.exists(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
        _model_version = str(int(os.path.getmtime(MODEL_PATH)))
    else:
        _model = None
        _model_version = "unloaded"


@app.on_event("startup")
def startup():
    load_model()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.get("/model/info")
def model_info():
    return {"model_version": _model_version, "model_path": MODEL_PATH}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start = time.time()
    request_id = str(uuid.uuid4())

    cache_key = "pred:" + hashlib.sha256(
        json.dumps(payload.dict(), sort_keys=True).encode()
    ).hexdigest()
    cached = redis_client.get(cache_key)
    if cached:
        result = json.loads(cached)
        REQUEST_COUNT.labels(result="cache_hit").inc()
        return result

    features = [[
        payload.age,
        payload.sleep_hours,
        payload.work_hours,
        payload.academic_pressure,
        payload.financial_stress,
        payload.social_support,
    ]]
    score = float(_model.predict_proba(features)[0][1])
    label = "high_risk" if score >= 0.5 else "low_risk"

    response = {
        "request_id": request_id,
        "risk_score": round(score, 4),
        "risk_label": label,
        "model_version": _model_version,
    }

    redis_client.setex(cache_key, 3600, json.dumps(response))

    with engine.begin() as conn:
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO predictions
                    (request_id, age, sleep_hours, work_hours, academic_pressure,
                     financial_stress, social_support, risk_score, risk_label, model_version)
                VALUES
                    (:request_id, :age, :sleep_hours, :work_hours, :academic_pressure,
                     :financial_stress, :social_support, :risk_score, :risk_label, :model_version)
                """
            ),
            {**payload.dict(), **response},
        )

    REQUEST_COUNT.labels(result=label).inc()
    REQUEST_LATENCY.observe(time.time() - start)
    return response
