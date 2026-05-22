from django.contrib import admin
from django.utils.html import format_html

from ai.admin_utils import DEFAULT_BADGE, badge, status_badge
from .models import RestaurantAIProfile, ReviewClassificationResult

STATUS_STYLE = {
    ReviewClassificationResult.STATUS_DONE:    ("#d4edda", "#155724", "분류 완료"),
    ReviewClassificationResult.STATUS_PENDING: ("#fff3cd", "#856404", "분류 대기"),
    ReviewClassificationResult.STATUS_FAILED:  ("#f8d7da", "#721c24", "분류 실패"),
}

ALLEY_TAG_COLORS = {
    "현지인 추천":    ("#cce5ff", "#004085"),
    "나만 알고 싶은": ("#d4edda", "#155724"),
    "친절함":        ("#fff3cd", "#856404"),
    "혜자로운":       ("#f8d7da", "#721c24"),
}


def _alley_badges(obj) -> str:
    if not obj.alley_tags:
        return "—"
    badges = [
        str(badge(*ALLEY_TAG_COLORS.get(tag, DEFAULT_BADGE),
                  f"{tag} ({obj.alley_tag_scores.get(tag, 0):.0%})"))
        for tag in obj.alley_tags
    ]
    return format_html(" ".join(badges))


def _dashboard_badges(obj) -> str:
    if not obj.dashboard_tags:
        return "—"
    return format_html(
        " ".join(str(badge("#e9ecef", "#495057", tag)) for tag in obj.dashboard_tags)
    )


def _ai_keyword_badges(obj) -> str:
    parts = (
        [str(badge("#d4edda", "#155724", f"↑{kw}")) for kw in obj.ai_positive_keywords]
        + [str(badge("#f8d7da", "#721c24", f"↓{kw}")) for kw in obj.ai_negative_keywords]
    )
    return format_html(" ".join(parts)) if parts else "—"


# ── 인라인 ────────────────────────────────────────────────────────────────────

class ReviewClassificationInline(admin.StackedInline):
    model           = ReviewClassificationResult
    extra           = 0
    can_delete      = False
    readonly_fields = [
        "status_badge", "alley_tags_display", "dashboard_tags_display",
        "ai_keywords_display", "analyzed_at", "error_msg",
    ]
    fields              = readonly_fields
    verbose_name        = "리뷰 분류 결과"
    verbose_name_plural = "리뷰 분류 결과"

    @admin.display(description="분류 상태")
    def status_badge(self, obj):
        return status_badge(obj.status, STATUS_STYLE)

    @admin.display(description="골목장인 태그")
    def alley_tags_display(self, obj):
        return _alley_badges(obj)

    @admin.display(description="대시보드 태그")
    def dashboard_tags_display(self, obj):
        return _dashboard_badges(obj)

    @admin.display(description="AI 카테고리")
    def ai_keywords_display(self, obj):
        return _ai_keyword_badges(obj)


# ── ReviewClassificationResultAdmin ──────────────────────────────────────────

@admin.register(ReviewClassificationResult)
class ReviewClassificationResultAdmin(admin.ModelAdmin):
    list_display  = [
        "review_content", "restaurant_name",
        "status_badge", "alley_tags_display", "dashboard_tags_display",
        "ai_keywords_display", "analyzed_at",
    ]
    list_filter   = ["status"]
    search_fields = ["review__content", "review__restaurant__name"]
    readonly_fields = [
        "review", "status_badge",
        "alley_tags_display", "alley_tag_scores",
        "dashboard_tags_display", "ai_keywords_display",
        "analyzed_at", "error_msg",
    ]
    fieldsets = [
        ("리뷰 정보",    {"fields": ["review"]}),
        ("분류 상태",    {"fields": ["status_badge", "analyzed_at"]}),
        ("골목장인 배지", {"fields": ["alley_tags_display", "alley_tag_scores"]}),
        ("대시보드 태그", {"fields": ["dashboard_tags_display"]}),
        ("AI 카테고리",  {"fields": ["ai_keywords_display"]}),
        ("오류 정보",    {"fields": ["error_msg"], "classes": ["collapse"]}),
    ]

    @admin.display(description="리뷰 내용")
    def review_content(self, obj):
        content = obj.review.content
        return content[:40] + "…" if len(content) > 40 else content

    @admin.display(description="식당")
    def restaurant_name(self, obj):
        return obj.review.restaurant.name

    @admin.display(description="분류 상태")
    def status_badge(self, obj):
        return status_badge(obj.status, STATUS_STYLE)

    @admin.display(description="골목장인 태그")
    def alley_tags_display(self, obj):
        return _alley_badges(obj)

    @admin.display(description="대시보드 태그")
    def dashboard_tags_display(self, obj):
        return _dashboard_badges(obj)

    @admin.display(description="AI 카테고리")
    def ai_keywords_display(self, obj):
        return _ai_keyword_badges(obj)


# ── RestaurantAIProfileAdmin ──────────────────────────────────────────────────

@admin.register(RestaurantAIProfile)
class RestaurantAIProfileAdmin(admin.ModelAdmin):
    list_display  = [
        "restaurant_name", "alley_badge_display", "ai_score_display",
        "positive_ratio_bar", "hygiene_alert_display",
        "review_count_analyzed", "last_calculated_at",
    ]
    list_filter   = ["is_alley_eligible", "hygiene_alert"]
    search_fields = ["restaurant__name"]
    ordering      = ["-last_calculated_at"]
    readonly_fields = [
        "restaurant",
        "alley_badge_display", "alley_review_ratio",
        "ai_score_display", "positive_ratio_bar",
        "top_positive_tags", "top_negative_tags", "dashboard_tag_summary",
        "hygiene_alert_display", "recent_hygiene_negative_ratio",
        "review_count_analyzed", "last_calculated_at",
    ]
    fieldsets = [
        ("식당",         {"fields": ["restaurant"]}),
        ("골목장인 배지", {"fields": ["alley_badge_display", "alley_review_ratio"]}),
        ("AI 점수",      {"fields": ["ai_score_display", "positive_ratio_bar"]}),
        ("대시보드 태그", {"fields": ["top_positive_tags", "top_negative_tags", "dashboard_tag_summary"],
                          "classes": ["collapse"]}),
        ("위생 경고",    {"fields": ["hygiene_alert_display", "recent_hygiene_negative_ratio"]}),
        ("메타",         {"fields": ["review_count_analyzed", "last_calculated_at"]}),
    ]

    @admin.display(description="식당명")
    def restaurant_name(self, obj):
        return obj.restaurant.name

    @admin.display(description="골목장인")
    def alley_badge_display(self, obj):
        if obj.is_alley_eligible:
            return badge("#ffd700", "#5a3e00", f"🏅 골목장인 ({obj.alley_review_ratio:.0%})")
        return badge("#e9ecef", "#495057", f"{obj.alley_review_ratio:.0%} / 70% 필요")

    @admin.display(description="AI 점수")
    def ai_score_display(self, obj):
        s = obj.ai_net_score
        color = "#155724" if s > 0 else ("#721c24" if s < 0 else "#495057")
        bg    = "#d4edda"  if s > 0 else ("#f8d7da"  if s < 0 else "#e9ecef")
        return badge(bg, color, f"{s:+d}점")

    @admin.display(description="긍정 비율 (90일)")
    def positive_ratio_bar(self, obj):
        pct   = int(obj.positive_ratio * 100)
        color = "#28a745" if obj.positive_ratio >= 0.80 else "#ffc107"
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:120px;background:#e9ecef;border-radius:4px;height:10px;">'
            '<div style="width:{}%;background:{};border-radius:4px;height:10px;"></div>'
            '</div>'
            '<span style="font-size:13px;font-weight:600;">{}%</span>'
            '</div>',
            pct, color, pct,
        )

    @admin.display(description="위생 경고")
    def hygiene_alert_display(self, obj):
        if obj.hygiene_alert:
            return badge("#f8d7da", "#721c24", f"⚠️ 경고 ({obj.recent_hygiene_negative_ratio:.0%})")
        return badge("#d4edda", "#155724", "정상")
