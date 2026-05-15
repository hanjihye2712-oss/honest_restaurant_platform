from django.contrib import admin
from .models import Bookmark, Rating, Review


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ["user", "restaurant", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "restaurant__name"]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["user", "restaurant", "score", "updated_at"]
    list_filter = ["score"]
    search_fields = ["user__username", "restaurant__name"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "restaurant", "content", "created_at"]
    search_fields = ["user__username", "restaurant__name", "content"]
