"""
interactions.urls
=================
URL 구성

페이지 뷰
    /bookmarks/   — 내 북마크 목록
    /reviews/     — 내 리뷰 목록

API (api/interactions/ 네임스페이스로 마운트)
    bookmarks/         — 북마크 목록 / 생성
    bookmarks/toggle/  — 북마크 토글
    ratings/           — 별점 upsert
    reviews/           — 리뷰 목록 / 생성
    reviews/{id}/      — 리뷰 수정 / 삭제
    restaurants/<pk>/review/ — 통합 삭제 (Axios)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookmarkListView,
    BookmarkViewSet,
    RatingViewSet,
    ReviewDeleteView,
    ReviewListView,
    ReviewViewSet,
)

router = DefaultRouter()
router.register("bookmarks", BookmarkViewSet, basename="bookmark")
router.register("ratings",   RatingViewSet,   basename="rating")
router.register("reviews",   ReviewViewSet,   basename="review")

# API 엔드포인트 (api/interactions/ 하위)
api_urlpatterns = [
    path("", include(router.urls)),
    path(
        "restaurants/<int:pk>/review/",
        ReviewDeleteView.as_view(),
        name="restaurant-review-action",
    ),
]

# 페이지 뷰 (루트 하위)
page_urlpatterns = [
    path("bookmarks/", BookmarkListView.as_view(), name="bookmark-list"),
    path("reviews/",   ReviewListView.as_view(),   name="review-list"),
]

# Django 기본 모듈 참조 호환용 (manage.py show_urls 등)
urlpatterns = api_urlpatterns + page_urlpatterns
