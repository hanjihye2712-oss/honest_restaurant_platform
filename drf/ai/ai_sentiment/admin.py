from django.contrib import admin

from ai.admin_utils import DEFAULT_BADGE, badge, score_bar, status_badge
from .models import SentimentResult

STATUS_STYLE = {
    SentimentResult.STATUS_DONE:    ("#d4edda", "#155724", "분석 완료"),
    SentimentResult.STATUS_PENDING: ("#fff3cd", "#856404", "분석 대기"),
    SentimentResult.STATUS_FAILED:  ("#f8d7da", "#721c24", "분석 실패"),
}
LABEL_STYLE = {
    "긍정": ("#d4edda", "#155724"),
    "부정": ("#f8d7da", "#721c24"),
}


class SentimentDisplayMixin:
    """status_badge, label_badge, score_bar — Inline과 Admin 공용."""

    @admin.display(description="분석 상태")
    def status_badge(self, obj):
        return status_badge(obj.status, STATUS_STYLE)

    @admin.display(description="감정")
    def label_badge(self, obj):
        if not obj.label:
            return "—"
        bg, color = LABEL_STYLE.get(obj.label, DEFAULT_BADGE)
        return badge(bg, color, obj.label, weight="700")

    @admin.display(description="신뢰도")
    def score_bar(self, obj):
        return score_bar(obj.score, obj.label)


class SentimentResultInline(SentimentDisplayMixin, admin.StackedInline):
    model               = SentimentResult
    extra               = 0
    can_delete          = False
    readonly_fields     = ["status_badge", "label_badge", "score_bar", "analyzed_at", "error_msg"]
    fields              = readonly_fields
    verbose_name        = "감성 분석 결과"
    verbose_name_plural = "감성 분석 결과"


@admin.register(SentimentResult)
class SentimentResultAdmin(SentimentDisplayMixin, admin.ModelAdmin):
    list_display    = ["review_content", "restaurant_name", "status_badge", "label_badge", "score_bar", "analyzed_at"]
    list_filter     = ["status", "label"]
    search_fields   = ["review__content", "review__restaurant__name"]
    readonly_fields = ["review", "status_badge", "label_badge", "score_bar", "analyzed_at", "error_msg"]
    fieldsets = [
        ("리뷰 정보", {"fields": ["review"]}),
        ("분석 결과", {"fields": ["status_badge", "label_badge", "score_bar", "analyzed_at"]}),
        ("오류 정보", {"fields": ["error_msg"], "classes": ["collapse"]}),
    ]

    @admin.display(description="리뷰 내용")
    def review_content(self, obj):
        content = obj.review.content
        return content[:40] + "…" if len(content) > 40 else content

    @admin.display(description="식당")
    def restaurant_name(self, obj):
        return obj.review.restaurant.name
