"""
interactions.pages_urls
=======================
템플릿 렌더링 페이지 전용 URL (API 엔드포인트 제외)
"""

from django.urls import path
from .views import BookmarkListView

urlpatterns = [
    path("", BookmarkListView.as_view(), name="bookmark-list"),
]
