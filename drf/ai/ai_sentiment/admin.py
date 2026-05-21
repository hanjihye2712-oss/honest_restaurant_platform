from django.contrib import admin
from django.utils.html import format_html

from .models import SentimentResult

# ──────────────────────────────────────────────────────────────
# 모듈 레벨 상수 — interactions/admin.py에서도 import해서 사용
# ──────────────────────────────────────────────────────────────

STATUS_STYLE = {
    SentimentResult.STATUS_DONE:    ("#d4edda", "#155724", "분석 완료"),
    SentimentResult.STATUS_PENDING: ("#fff3cd", "#856404", "분석 대기"),
    SentimentResult.STATUS_FAILED:  ("#f8d7da", "#721c24", "분석 실패"),
}
LABEL_STYLE = {
    "긍정": ("#d4edda", "#155724"),
    "부정": ("#f8d7da", "#721c24"),
}
DEFAULT_BADGE = ("#e9ecef", "#495057")


def _badge(bg: str, color: str, label: str, weight: str = "600") -> str:
    return format_html(
        '<span style="background:{};color:{};padding:3px 10px;'
        'border-radius:999px;font-size:12px;font-weight:{};">{}</span>',
        bg, color, weight, label,
    )


# ──────────────────────────────────────────────────────────────
# 공통 Mixin — Inline·Admin 양쪽에서 재사용
# ──────────────────────────────────────────────────────────────

class SentimentDisplayMixin:
    """status_badge, label_badge, score_bar — Inline과 Admin 공용."""

    @admin.display(description="분석 상태")
    def status_badge(self, obj):
        bg, color, label = STATUS_STYLE.get(obj.status, (*DEFAULT_BADGE, obj.status))
        return _badge(bg, color, label, weight="600")

    @admin.display(description="감정")
    def label_badge(self, obj):
        if not obj.label:
            return "—"
        bg, color = LABEL_STYLE.get(obj.label, DEFAULT_BADGE)
        return _badge(bg, color, obj.label, weight="700")

    @admin.display(description="신뢰도")
    def score_bar(self, obj):
        if obj.score is None:
            return "—"
        pct       = int(obj.score * 100)
        score_txt = f"{obj.score * 100:.1f}%"
        color     = "#28a745" if obj.label == "긍정" else "#dc3545"
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:120px;background:#e9ecef;border-radius:4px;height:10px;">'
            '<div style="width:{}%;background:{};border-radius:4px;height:10px;"></div>'
            '</div>'
            '<span style="font-size:13px;font-weight:600;">{}</span>'
            '</div>',
            pct, color, score_txt,
        )


# ──────────────────────────────────────────────────────────────
# SentimentResult 인라인 — ReviewAdmin 상세 페이지에서 함께 표시
# ──────────────────────────────────────────────────────────────

class SentimentResultInline(SentimentDisplayMixin, admin.StackedInline):
    model               = SentimentResult
    extra               = 0
    can_delete          = False
    readonly_fields     = ["status_badge", "label_badge", "score_bar", "analyzed_at", "error_msg"]
    fields              = ["status_badge", "label_badge", "score_bar", "analyzed_at", "error_msg"]
    verbose_name        = "감성 분석 결과"
    verbose_name_plural = "감성 분석 결과"


# ──────────────────────────────────────────────────────────────
# SentimentResultAdmin
# ──────────────────────────────────────────────────────────────

@admin.register(SentimentResult)
class SentimentResultAdmin(SentimentDisplayMixin, admin.ModelAdmin):
    list_display    = ["review_content", "restaurant_name", "status_badge", "label_badge", "score_bar", "analyzed_at"]
    list_filter     = ["status", "label"]
    search_fields   = ["review__content", "review__restaurant__name"]
    readonly_fields = ["review", "status_badge", "label_badge", "score_bar", "analyzed_at", "error_msg"]
    fieldsets = [
        ("리뷰 정보",  {"fields": ["review"]}),
        ("분석 결과",  {"fields": ["status_badge", "label_badge", "score_bar", "analyzed_at"]}),
        ("오류 정보",  {"fields": ["error_msg"], "classes": ["collapse"]}),
    ]

    @admin.display(description="리뷰 내용")
    def review_content(self, obj):
        content = obj.review.content
        return content[:40] + "…" if len(content) > 40 else content

    @admin.display(description="식당")
    def restaurant_name(self, obj):
        return obj.review.restaurant.name
