from pydantic import BaseModel, Field


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="분석할 텍스트")


class SentimentResponse(BaseModel):
    label: str = Field(..., description="긍정 / 부정")
    score: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")
