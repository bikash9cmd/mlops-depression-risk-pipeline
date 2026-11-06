import pandas as pd
import pytest

import preprocess

VALID_ROW = {
    "age": 21,
    "sleep_hours": 6.5,
    "work_hours": 8,
    "academic_pressure": 7,
    "financial_stress": 5,
    "social_support": 4,
}


def write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0, 0),
        (1, 1),
        (1.0, 1),
        ("0", 0),
        ("1", 1),
        ("low_risk", 0),
        ("high_risk", 1),
        (" High_Risk ", 1),
    ],
)
def test_normalize_labels_maps_known_values(raw, expected):
    assert preprocess.normalize_labels(pd.Series([raw])).tolist() == [expected]


@pytest.mark.parametrize("raw", ["medium", "2", 2, "", None])
def test_normalize_labels_marks_unknown_values_missing(raw):
    assert preprocess.normalize_labels(pd.Series([raw], dtype=object)).isna().all()


def test_load_and_clean_drops_unknown_labels(tmp_path):
    path = write_csv(
        tmp_path / "data.csv",
        [
            {**VALID_ROW, "risk_label": "high_risk"},
            {**VALID_ROW, "risk_label": "medium"},
        ],
    )
    df = preprocess.load_and_clean(path)
    assert df["risk_label"].tolist() == [1]
    assert df["risk_label"].dtype == int


@pytest.mark.parametrize(
    "column, value",
    [
        ("age", 9),
        ("age", 101),
        ("sleep_hours", 25),
        ("work_hours", -1),
        ("work_hours", 25),
        ("academic_pressure", 11),
        ("financial_stress", -0.5),
        ("social_support", 10.5),
        ("work_hours", "lots"),
    ],
)
def test_load_and_clean_drops_out_of_range_features(tmp_path, column, value):
    path = write_csv(
        tmp_path / "data.csv",
        [
            {**VALID_ROW, "risk_label": 1},
            {**VALID_ROW, column: value, "risk_label": 1},
        ],
    )
    assert len(preprocess.load_and_clean(path)) == 1


def test_bounds_match_api_schema():
    schema = pytest.importorskip("api.app.schemas", reason="pydantic not installed")
    fields = schema.PredictionRequest.model_fields
    for column, (low, high) in preprocess.FEATURE_BOUNDS.items():
        meta = {type(m).__name__: m for m in fields[column].metadata}
        assert meta["Ge"].ge == low
        assert meta["Le"].le == high


def test_main_merges_survey_and_logged_labels_into_binary_target(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    write_csv(
        raw / "depression_survey.csv",
        [
            {**VALID_ROW, "risk_label": 0},
            {**VALID_ROW, "age": 30, "risk_label": 1},
        ],
    )
    write_csv(
        raw / "logged_predictions.csv",
        [
            {**VALID_ROW, "age": 40, "risk_label": "high_risk"},
            {**VALID_ROW, "age": 50, "risk_label": "low_risk"},
        ],
    )
    monkeypatch.setattr(preprocess, "PROCESSED_DIR", str(processed))
    monkeypatch.setattr(preprocess, "BASE_FILE", str(raw / "depression_survey.csv"))
    monkeypatch.setattr(preprocess, "LOGGED_FILE", str(raw / "logged_predictions.csv"))
    monkeypatch.setattr(preprocess, "OUTPUT_FILE", str(processed / "training_data.csv"))

    preprocess.main()

    out = pd.read_csv(processed / "training_data.csv")
    assert len(out) == 4
    assert sorted(out["risk_label"].unique().tolist()) == [0, 1]
    assert out.loc[out["age"] == 40, "risk_label"].item() == 1
    assert out.loc[out["age"] == 50, "risk_label"].item() == 0
