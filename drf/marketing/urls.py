from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MarketingManagePageView, MarketingPostViewSet

app_name = 'marketing'

# ── API 라우터 ─────────────────────────────────────────
router = DefaultRouter()
router.register(r'api/posts', MarketingPostViewSet, basename='marketing-post')

# ── 페이지 URL ─────────────────────────────────────────
urlpatterns = [
    path('manage/', MarketingManagePageView.as_view(), name='manage'),
] + router.urls
