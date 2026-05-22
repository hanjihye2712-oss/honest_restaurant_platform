from django.db import models


class ReviewClassificationResult(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE    = "done"
    STATUS_FAILED  = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "분류 대기"),
        (STATUS_DONE,    "분류 완료"),
        (STATUS_FAILED,  "분류 실패"),
    ]

    review = models.OneToOneField(
        "interactions.Review",
        on_delete=models.CASCADE,
        related_name="review_classification",
        verbose_name="리뷰",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="분류 상태",
    )

    # 골목장인 배지용
    alley_tags = models.JSONField(
        default=list,
        verbose_name="골목장인 태그",
        help_text='예: ["현지인 추천", "나만 알고 싶은"]',
    )
    alley_tag_scores = models.JSONField(
        default=dict,
        verbose_name="골목장인 태그 신뢰도",
        help_text='예: {"현지인 추천": 0.82, "나만 알고 싶은": 0.71}',
    )

    # 사장님 대시보드용
    dashboard_tags = models.JSONField(
        default=list,
        verbose_name="대시보드 태그",
        help_text='예: ["맛있어요", "위생적이에요", "재방문이에요"]',
    )

    # AI 점수 계산용 (위생·재방문·응대·회전율)
    ai_positive_keywords = models.JSONField(
        default=list,
        verbose_name="AI 긍정 카테고리",
        help_text='예: ["위생", "재방문"]',
    )
    ai_negative_keywords = models.JSONField(
        default=list,
        verbose_name="AI 부정 카테고리",
        help_text='예: ["응대"]',
    )

    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name="분류 완료 시각")
    error_msg   = models.TextField(blank=True, verbose_name="오류 메시지")

    @classmethod
    def reset_for_review(cls, review_id: int) -> None:
        """리뷰 내용 수정 시 이전 분류 결과를 초기화한다."""
        cls.objects.filter(review_id=review_id).update(
            status               = cls.STATUS_PENDING,
            alley_tags           = [],
            alley_tag_scores     = {},
            dashboard_tags       = [],
            ai_positive_keywords = [],
            ai_negative_keywords = [],
            analyzed_at          = None,
            error_msg            = "",
        )

    def __str__(self):
        return f"{self.review} → {self.get_status_display()}"

    class Meta:
        db_table            = "review_classification_result"
        verbose_name        = "리뷰 분류 결과"
        verbose_name_plural = "리뷰 분류 결과"


# ── 식당 단위 AI 집계 프로필 ──────────────────────────────────────────────────

class RestaurantAIProfile(models.Model):
    """
    식당 단위로 ReviewClassificationResult + SentimentResult를 집계한 요약본.
    리뷰 분류 완료 시마다 Celery로 자동 갱신된다.
    """

    restaurant = models.OneToOneField(
        "honest_restaurant.PublicRestaurantData",
        on_delete=models.CASCADE,
        related_name="ai_profile",
        verbose_name="식당",
    )

    # 골목장인 배지
    alley_review_ratio = models.FloatField(default=0.0, verbose_name="골목장인 태그 보유 리뷰 비율")
    is_alley_eligible  = models.BooleanField(default=False, db_index=True, verbose_name="골목장인 자격")

    # AI 점수 (레벨화 기준 10점 만점, 90일 기준)
    positive_ratio   = models.FloatField(default=0.0, verbose_name="긍정 리뷰 비율 (90일)")
    negative_ratio   = models.FloatField(default=0.0, verbose_name="부정 리뷰 비율 (90일)")
    ai_score_bonus   = models.IntegerField(default=0, verbose_name="AI 보너스 점수")
    ai_score_penalty = models.IntegerField(default=0, verbose_name="AI 패널티 점수")
    ai_net_score     = models.IntegerField(default=0, db_index=True, verbose_name="AI 순점수")

    # 사장님 대시보드 태그 요약
    dashboard_tag_summary = models.JSONField(default=dict, verbose_name="전체 태그 빈도")
    top_positive_tags     = models.JSONField(default=dict, verbose_name="상위 긍정 태그 Top5")
    top_negative_tags     = models.JSONField(default=dict, verbose_name="상위 부정 태그 Top5")

    # 위생 경고 (최근 14일)
    recent_hygiene_negative_ratio = models.FloatField(default=0.0, verbose_name="최근 14일 위생 부정 비율")
    hygiene_alert                 = models.BooleanField(default=False, db_index=True, verbose_name="위생 경고")

    # 메타
    review_count_analyzed = models.IntegerField(default=0, verbose_name="집계 기준 리뷰 수")
    last_calculated_at    = models.DateTimeField(null=True, blank=True, verbose_name="최종 집계 시각")

    def __str__(self):
        badge = " 🏅골목장인" if self.is_alley_eligible else ""
        alert = " ⚠️위생경고" if self.hygiene_alert    else ""
        return f"{self.restaurant.name}{badge}{alert} (AI {self.ai_net_score:+d}점)"

    class Meta:
        db_table            = "restaurant_ai_profile"
        verbose_name        = "식당 AI 프로필"
        verbose_name_plural = "식당 AI 프로필"
