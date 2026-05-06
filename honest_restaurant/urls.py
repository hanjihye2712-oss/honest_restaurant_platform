from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (PublicRestaurantDataViewSet, restaurant_list_page, index_page,
                    restaurant_detail_page, receipt_verify_page,
                    media_upload, media_delete)

app_name = "public_restaurants"   # 임시 네임스페이스

# ── API 라우터 (JSON) ──────────────────────────
router = DefaultRouter()
router.register(
    prefix   = "public-restaurants",
    viewset  = PublicRestaurantDataViewSet,
    basename = "public-restaurant",   # 임시 basename
)

urlpatterns = [
    # 메인 페이지
    path("", index_page, name="index"),

    # JSON API
    path("api/", include(router.urls)),

    # 템플릿 페이지 (HTML)
    path("restaurants/", restaurant_list_page, name="restaurant-list-page"),
    path("restaurants/<int:pk>/", restaurant_detail_page, name="restaurant-detail-page"),
    path("restaurants/<int:pk>/verify/", receipt_verify_page, name="restaurant-verify"),
    path("restaurants/<int:pk>/media/upload/", media_upload, name="media-upload"),
    path("restaurants/<int:pk>/media/<int:media_pk>/delete/", media_delete, name="media-delete"),
]