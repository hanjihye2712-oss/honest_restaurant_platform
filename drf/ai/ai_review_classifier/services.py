import logging

import requests
from django.conf import settings
from django.utils import timezone

from .models import ReviewClassificationResult

logger = logging.getLogger(__name__)


def request_review_classification(review_id: int, text: str) -> None:
    """
    FastAPI /review-classifier/analyze 를 호출하고 결과를 저장한다.
    실패 시 status=failed, error_msg에 원인을 기록한다.
    """
    try:
        resp = requests.post(
            settings.FASTAPI_REVIEW_CLASSIFIER_URL,
            json={"text": text},
            timeout=settings.FASTAPI_REVIEW_CLASSIFIER_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        ReviewClassificationResult.objects.filter(review_id=review_id).update(
            status               = ReviewClassificationResult.STATUS_DONE,
            alley_tags           = data["alley_tags"],
            alley_tag_scores     = data["alley_tag_scores"],
            dashboard_tags       = data["dashboard_tags"],
            ai_positive_keywords = data["ai_positive_keywords"],
            ai_negative_keywords = data["ai_negative_keywords"],
            analyzed_at          = timezone.now(),
            error_msg            = "",
        )
        logger.info(
            "리뷰 분류 완료 review_id=%s alley_tags=%s dashboard_tags=%s",
            review_id, data["alley_tags"], data["dashboard_tags"],
        )
    except Exception as exc:
        logger.error("리뷰 분류 실패 review_id=%s: %s", review_id, exc)
        ReviewClassificationResult.objects.filter(review_id=review_id).update(
            status    = ReviewClassificationResult.STATUS_FAILED,
            error_msg = str(exc),
        )
        raise
