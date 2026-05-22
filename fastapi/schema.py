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


# ── 리뷰 분류 (골목장인 + 대시보드 + AI 카테고리) ─────────────────────

class ReviewClassifierRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="분류할 리뷰 텍스트")


class ReviewClassifierResponse(BaseModel):
    alley_tags:            list[str]        = Field(..., description="골목장인 배지 태그 목록")
    alley_tag_scores:      dict[str, float] = Field(..., description="골목장인 태그별 신뢰도 (0.0~1.0)")
    dashboard_tags:        list[str]        = Field(..., description="사장님 대시보드 태그 목록")
    ai_positive_keywords:  list[str]        = Field(..., description="AI 점수 긍정 카테고리 (위생·재방문·응대·회전율)")
    ai_negative_keywords:  list[str]        = Field(..., description="AI 점수 부정 카테고리")
