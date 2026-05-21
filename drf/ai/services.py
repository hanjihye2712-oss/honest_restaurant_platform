import logging

import requests
from django.conf import settings
from django.utils import timezone

from .models import SentimentResult

logger = logging.getLogger(__name__)


def request_sentiment(review_id: int, text: str) -> None:
    """
    FastAPI 감성 분석 서버를 호출하고 결과를 SentimentResult에 저장한다.
    실패 시 status=failed, error_msg에 원인을 기록한다.
    """
    url     = settings.FASTAPI_SENTIMENT_URL
    timeout = settings.FASTAPI_SENTIMENT_TIMEOUT
    try:
        resp = requests.post(url, json={"text": text}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        SentimentResult.objects.filter(review_id=review_id).update(
            status=SentimentResult.STATUS_DONE,
            label=data["label"],
            score=data["score"],
            analyzed_at=timezone.now(),
            error_msg="",
        )
        logger.info("감성 분석 완료 review_id=%s label=%s score=%s",
                    review_id, data["label"], data["score"])
    except Exception as exc:
        logger.error("감성 분석 실패 review_id=%s: %s", review_id, exc)
        SentimentResult.objects.filter(review_id=review_id).update(
            status=SentimentResult.STATUS_FAILED,
            error_msg=str(exc),
        )
        raise
