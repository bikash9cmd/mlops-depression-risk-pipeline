-- Initial schema for the depression risk pipeline
-- Runs automatically on first MariaDB container start

CREATE DATABASE IF NOT EXISTS depression_pipeline;
USE depression_pipeline;

CREATE TABLE IF NOT EXISTS predictions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    age INT,
    sleep_hours FLOAT,
    work_hours FLOAT,
    academic_pressure FLOAT,
    financial_stress FLOAT,
    social_support FLOAT,
    risk_score FLOAT NOT NULL,
    risk_label VARCHAR(16) NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_registry (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_version VARCHAR(32) NOT NULL,
    training_rows INT,
    f1_score FLOAT,
    roc_auc FLOAT,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS drift_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_path VARCHAR(255) NOT NULL,
    dataset_drift BOOLEAN,
    drifted_columns INT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_created_at ON predictions (created_at);
