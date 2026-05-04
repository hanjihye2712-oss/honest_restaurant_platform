from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PublicRestaurantDataViewSet, restaurant_list_page

app_name = "public_restaurants"   # 임시 네임스페이스

# ── API 라우터 (JSON) ──────────────────────────
router = DefaultRouter()
router.register(
    prefix   = "public-restaurants",
    viewset  = PublicRestaurantDataViewSet,
    basename = "public-restaurant",   # 임시 basename
)

urlpatterns = [
    # JSON API
    # GET /api/public-restaurants/
    # GET /api/public-restaurants/{id}/
    path("api/", include(router.urls)),

    # 템플릿 페이지 (HTML)
    # GET /restaurants/
    path(
        "restaurants/",
        restaurant_list_page,
        name="restaurant-list-page",
    ),
]