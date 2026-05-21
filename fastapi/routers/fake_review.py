from fastapi import APIRouter, HTTPException
from schema import FakeReviewRequest, FakeReviewResponse
from models.fake_review import detect

router = APIRouter(prefix="/fake-review", tags=["가짜 리뷰 탐지"])


@router.post("/detect", response_model=FakeReviewResponse, summary="가짜 리뷰 탐지")
def detect_fake_review(req: FakeReviewRequest) -> FakeReviewResponse:
    try:
        result = detect(req.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return FakeReviewResponse(**result)
