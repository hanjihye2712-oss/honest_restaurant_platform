import logging

import requests
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .models import FakeReviewResult

logger = logging.getLogger(__name__)

PENALTY_THRESHOLD = 0.85  # 신뢰도 85% 이상일 때만 패널티 부여


def request_fake_review_check(review_id: int, korean_text: str) -> None:
    """
    FastAPI /fake-review/detect 에 한국어 텍스트를 전달한다.
    번역(Helsinki-NLP)과 탐지는 FastAPI 내부에서 처리된다.
    """
    try:
        resp = requests.post(
            settings.FASTAPI_FAKE_REVIEW_URL,
            json={"text": korean_text},
            timeout=settings.FASTAPI_FAKE_REVIEW_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        is_penalized = data["is_fake"] and data["confidence"] >= PENALTY_THRESHOLD
        penalty      = FakeReviewResult.PENALTY_FAKE if is_penalized else 0

        FakeReviewResult.objects.filter(review_id=review_id).update(
            status          = FakeReviewResult.STATUS_DONE,
            is_fake         = data["is_fake"],
            confidence      = data["confidence"],
            translated_text = data["translated_text"],
            penalty_score   = penalty,
            analyzed_at     = timezone.now(),
            error_msg       = "",
        )
        logger.info("가짜 리뷰 탐지 완료 review_id=%s is_fake=%s confidence=%s",
                    review_id, data["is_fake"], data["confidence"])

        if is_penalized:
            _apply_penalty(review_id)

    except Exception as exc:
        logger.error("가짜 리뷰 탐지 실패 review_id=%s: %s", review_id, exc)
        FakeReviewResult.objects.filter(review_id=review_id).update(
            status    = FakeReviewResult.STATUS_FAILED,
            error_msg = str(exc),
        )
        raise


def _apply_penalty(review_id: int) -> None:
    """가짜 리뷰 확정 시 UserTrustScore에 패널티 적용."""
    from interactions.models import Review
    from accounts.models import UserTrustScore

    review = Review.objects.select_related("user").get(id=review_id)
    UserTrustScore.objects.filter(user=review.user).update(
        score      = F("score") + FakeReviewResult.PENALTY_FAKE,
        fake_count = F("fake_count") + 1,
    )
    logger.info("패널티 적용 user=%s penalty=%s",
                review.user.username, FakeReviewResult.PENALTY_FAKE)
