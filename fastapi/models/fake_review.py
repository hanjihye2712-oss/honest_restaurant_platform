import logging

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline, Pipeline
from config import FAKE_REVIEW_MODEL_NAME, TRANSLATION_MODEL_NAME

logger = logging.getLogger(__name__)

_tokenizer:  AutoTokenizer          | None = None
_trans_model: AutoModelForSeq2SeqLM | None = None
_detector:   Pipeline               | None = None


def load_models() -> None:
    global _tokenizer, _trans_model, _detector

    logger.info("번역 모델 로딩 중: %s", TRANSLATION_MODEL_NAME)
    _tokenizer   = AutoTokenizer.from_pretrained(TRANSLATION_MODEL_NAME)
    _trans_model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL_NAME)
    logger.info("번역 모델 로딩 완료")

    logger.info("가짜 리뷰 탐지 모델 로딩 중: %s", FAKE_REVIEW_MODEL_NAME)
    _detector = pipeline("text-classification", model=FAKE_REVIEW_MODEL_NAME)
    logger.info("가짜 리뷰 탐지 모델 로딩 완료")


def _translate_ko_to_en(text: str) -> str:
    if _tokenizer is None or _trans_model is None:
        raise RuntimeError("번역 모델이 로드되지 않았습니다.")
    inputs = _tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = _trans_model.generate(**inputs, max_length=512)
    return _tokenizer.decode(outputs[0], skip_special_tokens=True)


def detect(korean_text: str) -> dict:
    if _detector is None:
        raise RuntimeError("가짜 리뷰 탐지 모델이 로드되지 않았습니다.")

    english_text = _translate_ko_to_en(korean_text)

    result     = _detector(english_text[:512])[0]
    is_fake    = result["label"].upper() in ("FAKE", "LABEL_1", "1")
    confidence = round(float(result["score"]), 4)

    return {
        "is_fake":         is_fake,
        "confidence":      confidence,
        "translated_text": english_text,
    }
