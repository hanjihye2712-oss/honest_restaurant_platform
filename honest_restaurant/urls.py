from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IndexView,
    MediaDeleteView,
    MediaUploadView,
    OwnerDashboardView,
    ReceiptVerifyView,
    RestaurantDetailView,
    RestaurantListView,
    RestaurantViewSet,
    VerifyCancelView,
)

app_name = "public_restaurants"

router = DefaultRouter()
router.register("public-restaurants", RestaurantViewSet, basename="public-restaurant")

# restaurants/<int:pk>/ 하위 URL — 공통 prefix 한 번만 선언
_restaurant_detail_urls = [
    path("",                             RestaurantDetailView.as_view(), name="restaurant-detail-page"),
    path("verify/",                      ReceiptVerifyView.as_view(),    name="restaurant-verify"),
    path("verify/cancel/",               VerifyCancelView.as_view(),     name="verify-cancel"),
    path("media/upload/",                MediaUploadView.as_view(),      name="media-upload"),
    path("media/<int:media_pk>/delete/", MediaDeleteView.as_view(),      name="media-delete"),
]

urlpatterns = [
    path("",            IndexView.as_view(),          name="index"),
    path("dashboard/",  OwnerDashboardView.as_view(), name="owner-dashboard"),
    path("api/",                      include(router.urls)),
    path("restaurants/",              RestaurantListView.as_view(), name="restaurant-list-page"),
    path("restaurants/<int:pk>/",     include(_restaurant_detail_urls)),
]
