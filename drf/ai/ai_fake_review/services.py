import logging

import requests
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .models import FakeReviewResult

logger = logging.getLogger(__name__)

PENALTY_THRESHOLD = 0.85  # 신뢰도 85% 이상일 때만 패널티 부여


def _translate_ko_to_en(text: str) -> str:
    """파파고 API로 한국어 → 영어 번역."""
    resp = requests.post(
        "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation",
        headers={
            "X-NCP-APIGW-API-KEY-ID": settings.PAPAGO_CLIENT_ID,
            "X-NCP-APIGW-API-KEY":    settings.PAPAGO_CLIENT_SECRET,
        },
        data={"source": "ko", "target": "en", "text": text},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()["message"]["result"]["translatedText"]


def request_fake_review_check(review_id: int, korean_text: str) -> None:
    """
    ① 파파고로 한국어 → 영어 번역
    ② FastAPI /fake-review/detect 에 영문 전달
    ③ 결과 저장 + 패널티 적용
    """
    try:
        # ① 번역
        english_text = _translate_ko_to_en(korean_text)

        # ② 가짜 탐지
        resp = requests.post(
            settings.FASTAPI_FAKE_REVIEW_URL,
            json={"text": english_text},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        is_penalized = data["is_fake"] and data["confidence"] >= PENALTY_THRESHOLD
        penalty      = FakeReviewResult.PENALTY_FAKE if is_penalized else 0

        # ③ 결과 저장
        FakeReviewResult.objects.filter(review_id=review_id).update(
            status          = FakeReviewResult.STATUS_DONE,
            is_fake         = data["is_fake"],
            confidence      = data["confidence"],
            translated_text = english_text,
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
