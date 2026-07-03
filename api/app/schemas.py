from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    age: int = Field(..., ge=10, le=100)
    sleep_hours: float = Field(..., ge=0, le=24)
    work_hours: float = Field(..., ge=0, le=24)
    academic_pressure: float = Field(..., ge=0, le=10)
    financial_stress: float = Field(..., ge=0, le=10)
    social_support: float = Field(..., ge=0, le=10)


class PredictionResponse(BaseModel):
    request_id: str
    risk_score: float
    risk_label: str
    model_version: str
