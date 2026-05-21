import logging
from transformers import pipeline, Pipeline
from config import FAKE_REVIEW_MODEL_NAME

logger = logging.getLogger(__name__)

_detector: Pipeline | None = None


def load_model() -> Pipeline:
    global _detector
    logger.info("가짜 리뷰 탐지 모델 로딩 중: %s", FAKE_REVIEW_MODEL_NAME)
    _detector = pipeline("text-classification", model=FAKE_REVIEW_MODEL_NAME)
    logger.info("가짜 리뷰 탐지 모델 로딩 완료")
    return _detector


def get_model() -> Pipeline:
    if _detector is None:
        raise RuntimeError("가짜 리뷰 탐지 모델이 로드되지 않았습니다. lifespan 설정을 확인하세요.")
    return _detector


def detect(english_text: str) -> dict:
    detector = get_model()
    result   = detector(english_text[:512])[0]
    # 모델 레이블에 따라 가짜 여부 판단 (FAKE or LABEL_1)
    is_fake    = result["label"].upper() in ("FAKE", "LABEL_1", "1")
    confidence = round(float(result["score"]), 4)
    return {"is_fake": is_fake, "confidence": confidence}
