"""
식당 단위 AI 집계 로직.

리뷰 분류 완료 시마다 tasks.py → recalculate_ai_profile 태스크에서 호출된다.
직접 호출 시: from ai.ai_review_classifier.aggregator import aggregate_restaurant_ai
"""

import logging
from collections import Counter
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# 부정적 의미를 가진 대시보드 태그 목록
_NEGATIVE_TAGS = frozenset({
    "불결해요", "불친절해요", "느린 서비스",
    "재방문 없어요", "비싸요", "양이 적어요",
})

# AI 점수 보너스/패널티 구간 (레벨화 기준 정리.md 기준)
_BONUS_TABLE  = [(0.95, 10), (0.90, 6), (0.80, 3)]
_PENALTY_TABLE = [(0.40, -10), (0.30, -6), (0.15, -3)]


def _calc_score(ratio: float, table: list[tuple[float, int]]) -> int:
    for threshold, score in table:
        if ratio >= threshold:
            return score
    return 0


def aggregate_restaurant_ai(restaurant_id: int) -> None:
    """
    ReviewClassificationResult + SentimentResult를 집계해 RestaurantAIProfile을 갱신한다.
    분석된 리뷰가 없으면 조용히 종료한다.
    """
    from honest_restaurant.models import PublicRestaurantData
    from ai.ai_sentiment.models import SentimentResult
    from .models import ReviewClassificationResult, RestaurantAIProfile

    now        = timezone.now()
    cutoff_90d = now - timedelta(days=90)
    cutoff_14d = now - timedelta(days=14)

    # ── 분류 완료된 리뷰 데이터 ────────────────────────────────────────
    rows = list(
        ReviewClassificationResult.objects.filter(
            review__restaurant_id=restaurant_id,
            status=ReviewClassificationResult.STATUS_DONE,
        ).values(
            "alley_tags",
            "dashboard_tags",
            "ai_negative_keywords",
            "review__created_at",
        )
    )

    total = len(rows)
    if total == 0:
        logger.info("aggregate_restaurant_ai: restaurant_id=%s 분류 데이터 없음, 종료", restaurant_id)
        return

    # ── 골목장인 태그 비율 ─────────────────────────────────────────────
    alley_count = sum(1 for r in rows if r["alley_tags"])
    alley_ratio = alley_count / total

    # ── 대시보드 태그 빈도 집계 ────────────────────────────────────────
    tag_counter: Counter = Counter()
    for r in rows:
        tag_counter.update(r["dashboard_tags"] or [])

    dashboard_summary = dict(tag_counter.most_common())
    top_positive_tags = {
        k: v for k, v in tag_counter.most_common(10)
        if k not in _NEGATIVE_TAGS
    }
    top_positive_tags = dict(list(top_positive_tags.items())[:5])
    top_negative_tags = dict(
        sorted(
            [(k, v) for k, v in tag_counter.items() if k in _NEGATIVE_TAGS],
            key=lambda x: -x[1],
        )[:5]
    )

    # ── 위생 경고: 최근 14일 위생 부정 비율 ────────────────────────────
    from django.conf import settings as _settings
    _hygiene_threshold = getattr(_settings, "HYGIENE_ALERT_THRESHOLD", 0.30)

    recent_rows    = [r for r in rows if r["review__created_at"] >= cutoff_14d]
    recent_total   = len(recent_rows)
    hygiene_neg    = sum(
        1 for r in recent_rows
        if "위생" in (r["ai_negative_keywords"] or [])
    )
    hygiene_ratio  = hygiene_neg / recent_total if recent_total > 0 else 0.0
    hygiene_alert  = hygiene_ratio >= _hygiene_threshold

    # ── 감성 비율 (90일, SentimentResult 기준) ─────────────────────────
    sentiment_qs     = SentimentResult.objects.filter(
        review__restaurant_id=restaurant_id,
        status=SentimentResult.STATUS_DONE,
        review__created_at__gte=cutoff_90d,
    )
    total_sentiment  = sentiment_qs.count()
    positive_count   = sentiment_qs.filter(label="긍정").count() if total_sentiment else 0
    negative_count   = sentiment_qs.filter(label="부정").count() if total_sentiment else 0
    positive_ratio   = positive_count / total_sentiment if total_sentiment else 0.0
    negative_ratio   = negative_count / total_sentiment if total_sentiment else 0.0

    ai_bonus   = _calc_score(positive_ratio, _BONUS_TABLE)
    ai_penalty = _calc_score(negative_ratio, _PENALTY_TABLE)

    # ── 골목장인 자격 (영업 3년 이상 + 태그 비율 70% 이상) ─────────────
    restaurant   = PublicRestaurantData.objects.get(pk=restaurant_id)
    operating_ok = (restaurant.operating_years or 0) >= 3
    is_alley_eligible = operating_ok and alley_ratio >= 0.70

    # ── 저장 ──────────────────────────────────────────────────────────
    RestaurantAIProfile.objects.update_or_create(
        restaurant_id=restaurant_id,
        defaults={
            "alley_review_ratio":             round(alley_ratio, 4),
            "is_alley_eligible":              is_alley_eligible,
            "positive_ratio":                 round(positive_ratio, 4),
            "negative_ratio":                 round(negative_ratio, 4),
            "ai_score_bonus":                 ai_bonus,
            "ai_score_penalty":               ai_penalty,
            "ai_net_score":                   ai_bonus + ai_penalty,
            "dashboard_tag_summary":          dashboard_summary,
            "top_positive_tags":              top_positive_tags,
            "top_negative_tags":              top_negative_tags,
            "recent_hygiene_negative_ratio":  round(hygiene_ratio, 4),
            "hygiene_alert":                  hygiene_alert,
            "review_count_analyzed":          total,
            "last_calculated_at":             now,
        },
    )
    logger.info(
        "AI 프로필 집계 완료 restaurant_id=%s alley=%.0f%% ai=%+d 위생경고=%s",
        restaurant_id, alley_ratio * 100, ai_bonus + ai_penalty, hygiene_alert,
    )
