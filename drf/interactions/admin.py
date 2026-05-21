from django.contrib import admin
from django.utils.html import format_html

from ai.admin import DEFAULT_BADGE, STATUS_STYLE, SentimentResultInline
from ai.models import SentimentResult
from .models import Bookmark, Rating, Review


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display  = ["user", "restaurant", "created_at"]
    list_filter   = ["created_at"]
    search_fields = ["user__username", "restaurant__name"]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display  = ["user", "restaurant", "score", "updated_at"]
    list_filter   = ["score"]
    search_fields = ["user__username", "restaurant__name"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display    = ["user", "restaurant", "content_preview", "sentiment_status", "created_at"]
    search_fields   = ["user__username", "restaurant__name", "content"]
    list_filter     = ["created_at"]
    readonly_fields = ["created_at", "updated_at"]
    inlines         = [SentimentResultInline]

    _STATUS_LABELS_SHORT = {
        SentimentResult.STATUS_DONE:    "완료",
        SentimentResult.STATUS_PENDING: "대기",
        SentimentResult.STATUS_FAILED:  "실패",
    }

    @admin.display(description="리뷰 내용")
    def content_preview(self, obj):
        return obj.content[:40] + "…" if len(obj.content) > 40 else obj.content

    @admin.display(description="분석 상태")
    def sentiment_status(self, obj):
        try:
            s = obj.sentiment
        except SentimentResult.DoesNotExist:
            return "—"
        bg, color, _ = STATUS_STYLE.get(s.status, (*DEFAULT_BADGE, s.status))
        label        = self._STATUS_LABELS_SHORT.get(s.status, s.status)
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:999px;font-size:12px;">{}</span>',
            bg, color, label,
        )
