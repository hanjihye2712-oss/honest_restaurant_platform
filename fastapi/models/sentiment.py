import logging
from transformers import pipeline, Pipeline
from config import MODEL_NAME

logger = logging.getLogger(__name__)

_clf: Pipeline | None = None


def load_pipeline() -> Pipeline:
    global _clf
    logger.info("모델 로딩 중: %s", MODEL_NAME)
    _clf = pipeline("text-classification", model=MODEL_NAME)
    logger.info("모델 로딩 완료")
    return _clf


def get_pipeline() -> Pipeline:
    if _clf is None:
        raise RuntimeError("모델이 로드되지 않았습니다. lifespan 설정을 확인하세요.")
    return _clf


def predict(text: str) -> dict:
    clf = get_pipeline()
    result = clf(text)[0]
    # LABEL_1 = 긍정, LABEL_0 = 부정
    label = "긍정" if "1" in result["label"] else "부정"
    return {"label": label, "score": round(float(result["score"]), 4)}
