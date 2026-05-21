from django.db import models


class FakeReviewResult(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE    = "done"
    STATUS_FAILED  = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "분석 대기"),
        (STATUS_DONE,    "분석 완료"),
        (STATUS_FAILED,  "분석 실패"),
    ]

    PENALTY_FAKE = -10

    review = models.OneToOneField(
        "interactions.Review",
        on_delete=models.CASCADE,
        related_name="fake_review",
        verbose_name="리뷰",
    )
    status          = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default=STATUS_PENDING, db_index=True, verbose_name="분석 상태",
    )
    is_fake         = models.BooleanField(null=True, blank=True, verbose_name="가짜 여부")
    confidence      = models.FloatField(null=True, blank=True, verbose_name="신뢰도")
    translated_text = models.TextField(blank=True, verbose_name="번역된 영문 텍스트")
    penalty_score   = models.IntegerField(default=0, verbose_name="부여된 패널티 점수")
    analyzed_at     = models.DateTimeField(null=True, blank=True, verbose_name="분석 완료 시각")
    error_msg       = models.TextField(blank=True, verbose_name="오류 메시지")

    def __str__(self):
        return f"{self.review} → {self.get_status_display()}"

    class Meta:
        db_table            = "fake_review_result"
        verbose_name        = "가짜 리뷰 탐지 결과"
        verbose_name_plural = "가짜 리뷰 탐지 결과"
