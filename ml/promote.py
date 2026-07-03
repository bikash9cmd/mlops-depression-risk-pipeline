"""
Compares the newly trained model's F1 score against the currently
active model in model_registry. If it's better, marks it active and
copies it to the well-known path the FastAPI service loads on startup.
"""

import os
import json
import shutil
import sqlalchemy

MODEL_DIR = "/opt/airflow/models"
ACTIVE_MODEL_PATH = os.path.join(MODEL_DIR, "depression_risk_model.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "latest_metadata.json")

DB_URL = "mysql+pymysql://{user}:{pwd}@{host}:3306/{db}".format(
    user=os.getenv("MARIADB_USER", "airflow"),
    pwd=os.getenv("MARIADB_PASSWORD", "airflow"),
    host=os.getenv("MARIADB_HOST", "mariadb"),
    db=os.getenv("MARIADB_DATABASE", "depression_pipeline"),
)


def main():
    with open(METADATA_PATH) as fh:
        candidate = json.load(fh)

    engine = sqlalchemy.create_engine(DB_URL)
    with engine.begin() as conn:
        current_best = conn.execute(
            sqlalchemy.text(
                "SELECT model_version, f1_score FROM model_registry WHERE is_active = TRUE LIMIT 1"
            )
        ).fetchone()

        should_promote = current_best is None or candidate["f1_score"] > current_best.f1_score

        if should_promote:
            conn.execute(sqlalchemy.text("UPDATE model_registry SET is_active = FALSE"))
            conn.execute(
                sqlalchemy.text(
                    "UPDATE model_registry SET is_active = TRUE WHERE model_version = :v"
                ),
                {"v": candidate["version"]},
            )
            shutil.copyfile(candidate["model_path"], ACTIVE_MODEL_PATH)
            print(f"Promoted model {candidate['version']} to production.")
        else:
            print(
                f"Candidate {candidate['version']} (f1={candidate['f1_score']:.4f}) "
                f"did not beat current best (f1={current_best.f1_score:.4f}); not promoted."
            )


if __name__ == "__main__":
    main()
