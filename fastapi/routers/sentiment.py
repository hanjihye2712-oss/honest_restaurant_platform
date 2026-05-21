from fastapi import APIRouter, HTTPException
from schema import SentimentRequest, SentimentResponse
from models.sentiment import predict

router = APIRouter()


@router.post("/analyze", response_model=SentimentResponse, summary="감성 분석")
def analyze(req: SentimentRequest) -> SentimentResponse:
    try:
        result = predict(req.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return SentimentResponse(**result)


@router.get("/health", summary="헬스 체크")
def health() -> dict:
    return {"status": "ok"}
