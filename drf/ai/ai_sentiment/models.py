from django.db import models


class SentimentResult(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE    = "done"
    STATUS_FAILED  = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "분석 대기"),
        (STATUS_DONE,    "분석 완료"),
        (STATUS_FAILED,  "분석 실패"),
    ]

    review = models.OneToOneField(
        "interactions.Review",
        on_delete=models.CASCADE,
        related_name="sentiment",
        verbose_name="리뷰",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="분석 상태",
    )
    label = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="감정 레이블",
        help_text="긍정 / 부정",
    )
    score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="신뢰도",
        help_text="0.0 ~ 1.0",
    )
    analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="분석 완료 시각",
    )
    error_msg = models.TextField(
        blank=True,
        verbose_name="오류 메시지",
    )

    @classmethod
    def reset_for_review(cls, review_id: int) -> None:
        """리뷰 내용 수정 시 이전 분석 결과를 초기화하고 pending으로 되돌린다."""
        cls.objects.filter(review_id=review_id).update(
            status=cls.STATUS_PENDING,
            label=None,
            score=None,
            analyzed_at=None,
            error_msg="",
        )

    def __str__(self):
        return f"{self.review} → {self.get_status_display()}"

    class Meta:
        db_table = "sentiment_result"
        verbose_name = "감성 분석 결과"
        verbose_name_plural = "감성 분석 결과"
