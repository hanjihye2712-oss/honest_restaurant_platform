from pydantic import BaseModel, Field


# ── 감성 분석 ─────────────────────────────────────────────────

class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="분석할 텍스트")


class SentimentResponse(BaseModel):
    label: str   = Field(..., description="긍정 / 부정")
    score: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")


# ── 가짜 리뷰 탐지 ────────────────────────────────────────────

class FakeReviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="한국어 원문 텍스트")


class FakeReviewResponse(BaseModel):
    is_fake:         bool  = Field(..., description="True = 가짜, False = 정상")
    confidence:      float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")
    translated_text: str   = Field(..., description="번역된 영문 텍스트 (감사 추적용)")
