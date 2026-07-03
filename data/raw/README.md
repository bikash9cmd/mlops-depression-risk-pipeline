Place the base training CSV here as `depression_survey.csv`.

Expected columns:

```
age, sleep_hours, work_hours, academic_pressure, financial_stress, social_support, risk_label
```

`risk_label` should be binary (0 = low risk, 1 = high risk). The
original dataset used for this project was a cleaned student mental
health survey and is not included in this repo for privacy reasons -
swap in your own labeled data with the same schema.

`logged_predictions.csv` is generated automatically by
`ml/extract_logs.py` and should not be committed.
