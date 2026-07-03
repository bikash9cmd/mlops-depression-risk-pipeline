"""
Pulls new rows from the `predictions` table in MariaDB and appends them
to the raw training pool so the model can be periodically retrained on
real traffic rather than only the original static dataset.
"""

import os
import pandas as pd
import sqlalchemy

DB_URL = "mysql+pymysql://{user}:{pwd}@{host}:3306/{db}".format(
    user=os.getenv("MARIADB_USER", "airflow"),
    pwd=os.getenv("MARIADB_PASSWORD", "airflow"),
    host=os.getenv("MARIADB_HOST", "mariadb"),
    db=os.getenv("MARIADB_DATABASE", "depression_pipeline"),
)

OUTPUT_PATH = "/opt/airflow/data/raw/logged_predictions.csv"


def main():
    engine = sqlalchemy.create_engine(DB_URL)
    query = """
        SELECT age, sleep_hours, work_hours, academic_pressure,
               financial_stress, social_support, risk_label
        FROM predictions
        WHERE created_at >= NOW() - INTERVAL 1 DAY
    """
    df = pd.read_sql(query, engine)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    if os.path.exists(OUTPUT_PATH):
        existing = pd.read_csv(OUTPUT_PATH)
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates()

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
