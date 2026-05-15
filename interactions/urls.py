"""
interactions.urls
=================
URL 구성

    /api/interactions/bookmarks/         — 북마크 목록 / 생성
    /api/interactions/bookmarks/toggle/  — 북마크 토글
    /api/interactions/ratings/           — 별점 upsert
    /api/interactions/reviews/           — 리뷰 목록 / 생성
    /api/interactions/reviews/{id}/      — 리뷰 수정 / 삭제
    /api/interactions/restaurants/<pk>/review/ — 통합 삭제 (Axios)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookmarkViewSet,
    RatingViewSet,
    ReviewDeleteView,
    ReviewViewSet,
)

router = DefaultRouter()
router.register("bookmarks", BookmarkViewSet, basename="bookmark")
router.register("ratings",   RatingViewSet,   basename="rating")
router.register("reviews",   ReviewViewSet,   basename="review")

urlpatterns = [
    path("", include(router.urls)),

    # 리뷰 + 별점 + 영수증 인증 통합 삭제
    path(
        "restaurants/<int:pk>/review/",
        ReviewDeleteView.as_view(),
        name="restaurant-review-action",
    ),

]
