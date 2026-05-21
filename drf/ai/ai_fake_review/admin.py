from django.contrib import admin
from django.utils.html import format_html

from ai.ai_sentiment.admin import DEFAULT_BADGE, _badge
from .models import FakeReviewResult

_STATUS_STYLE = {
    FakeReviewResult.STATUS_DONE:    ("#d4edda", "#155724", "분석 완료"),
    FakeReviewResult.STATUS_PENDING: ("#fff3cd", "#856404", "분석 대기"),
    FakeReviewResult.STATUS_FAILED:  ("#f8d7da", "#721c24", "분석 실패"),
}


class FakeReviewDisplayMixin:
    """status_badge, is_fake_badge, confidence_bar — Inline·Admin 공용."""

    @admin.display(description="분석 상태")
    def status_badge(self, obj):
        bg, color, label = _STATUS_STYLE.get(obj.status, (*DEFAULT_BADGE, obj.status))
        return _badge(bg, color, label)

    @admin.display(description="가짜 여부")
    def is_fake_badge(self, obj):
        if obj.is_fake is None:
            return "—"
        bg, color, label = ("#f8d7da", "#721c24", "가짜") if obj.is_fake \
                      else ("#d4edda", "#155724", "정상")
        return _badge(bg, color, label, weight="700")

    @admin.display(description="신뢰도")
    def confidence_bar(self, obj):
        if obj.confidence is None:
            return "—"
        pct       = int(obj.confidence * 100)
        score_txt = f"{obj.confidence * 100:.1f}%"
        color     = "#dc3545" if obj.is_fake else "#28a745"
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:120px;background:#e9ecef;border-radius:4px;height:10px;">'
            '<div style="width:{}%;background:{};border-radius:4px;height:10px;"></div>'
            '</div><span style="font-size:13px;font-weight:600;">{}</span></div>',
            pct, color, score_txt,
        )


class FakeReviewResultInline(FakeReviewDisplayMixin, admin.StackedInline):
    model           = FakeReviewResult
    extra           = 0
    can_delete      = False
    readonly_fields = ["status_badge", "is_fake_badge", "confidence_bar",
                       "penalty_score", "analyzed_at", "error_msg"]
    fields          = ["status_badge", "is_fake_badge", "confidence_bar",
                       "penalty_score", "analyzed_at", "error_msg"]
    verbose_name        = "가짜 리뷰 탐지 결과"
    verbose_name_plural = "가짜 리뷰 탐지 결과"


@admin.register(FakeReviewResult)
class FakeReviewResultAdmin(FakeReviewDisplayMixin, admin.ModelAdmin):
    list_display    = ["review_content", "status_badge", "is_fake_badge",
                       "confidence_bar", "penalty_score", "analyzed_at"]
    list_filter     = ["status", "is_fake"]
    search_fields   = ["review__content", "review__user__username"]
    readonly_fields = ["review", "status_badge", "is_fake_badge", "confidence_bar",
                       "translated_text", "penalty_score", "analyzed_at", "error_msg"]
    fieldsets = [
        ("리뷰 정보",  {"fields": ["review"]}),
        ("탐지 결과",  {"fields": ["status_badge", "is_fake_badge",
                                   "confidence_bar", "penalty_score", "analyzed_at"]}),
        ("번역 텍스트", {"fields": ["translated_text"], "classes": ["collapse"]}),
        ("오류 정보",  {"fields": ["error_msg"], "classes": ["collapse"]}),
    ]

    @admin.display(description="리뷰 내용")
    def review_content(self, obj):
        content = obj.review.content
        return content[:40] + "…" if len(content) > 40 else content
