from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from .views import (
    DistrictListView,
    IndexView,
    MapMarkersView,
    MediaDeleteView,
    MediaUploadView,
    MenuItemCreateView,
    MenuItemDeleteView,
    MenuItemReorderView,
    MenuItemUpdateView,
    OwnerDashboardView,
    OwnerVerifyView,
    ReceiptVerifyView,
    RegisterRestaurantView,
    RestaurantDetailView,
    RestaurantInfoUpdateView,
    RestaurantListView,
    RestaurantViewSet,
    TaglineUpdateView,
    VerifyCancelView,
)

app_name = "public_restaurants"

router = DefaultRouter()
router.register("public-restaurants", RestaurantViewSet, basename="public-restaurant")

# restaurants/<int:pk>/ 하위 URL — 공통 prefix 한 번만 선언
_restaurant_detail_urls = [
    path("",                             RestaurantDetailView.as_view(),       name="restaurant-detail-page"),
    path("info/update/",                 RestaurantInfoUpdateView.as_view(),   name="restaurant-info-update"),
    path("tagline/update/",              TaglineUpdateView.as_view(),          name="tagline-update"),
    path("verify/",                      ReceiptVerifyView.as_view(),     name="restaurant-verify"),
    path("verify/cancel/",               VerifyCancelView.as_view(),      name="verify-cancel"),
    path("menu-items/",                          MenuItemCreateView.as_view(),  name="menu-item-create"),
    path("menu-items/reorder/",                  MenuItemReorderView.as_view(), name="menu-item-reorder"),
    path("menu-items/<int:item_pk>/update/",     MenuItemUpdateView.as_view(),  name="menu-item-update"),
    path("menu-items/<int:item_pk>/delete/",     MenuItemDeleteView.as_view(),  name="menu-item-delete"),
    path("media/upload/",                MediaUploadView.as_view(),       name="media-upload"),
    path("media/<int:media_pk>/delete/", MediaDeleteView.as_view(),       name="media-delete"),
]

urlpatterns = [
    path("",                      IndexView.as_view(),              name="index"),
    path("dashboard/",            OwnerDashboardView.as_view(),     name="owner-dashboard"),
    path("register-restaurant/",              RegisterRestaurantView.as_view(), name="register-restaurant"),
    path("register-restaurant/<int:pk>/verify/", OwnerVerifyView.as_view(),       name="verify-ownership"),
    path("api/",                      include(router.urls)),
    path("restaurants/districts/",     DistrictListView.as_view(),   name="district-list"),
    path("restaurants/map-markers/",   MapMarkersView.as_view(),     name="map-markers"),
    path("restaurants/",              RestaurantListView.as_view(), name="restaurant-list-page"),
    path("restaurants/<int:pk>/",     include(_restaurant_detail_urls)),
    path("sidenav-preview/", TemplateView.as_view(template_name="honest_restaurant/sidenav_preview.html"), name="sidenav-preview"),
]
