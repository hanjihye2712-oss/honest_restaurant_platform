from fastapi import APIRouter, HTTPException

from models.review_classifier import classify
from schema import ReviewClassifierRequest, ReviewClassifierResponse

router = APIRouter(prefix="/review-classifier", tags=["리뷰 분류"])


@router.post(
    "/analyze",
    response_model=ReviewClassifierResponse,
    summary="리뷰 분류 (골목장인 태그 + 대시보드 태그 + AI 카테고리)",
)
def analyze_review(req: ReviewClassifierRequest) -> ReviewClassifierResponse:
    try:
        result = classify(req.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return ReviewClassifierResponse(**result)
