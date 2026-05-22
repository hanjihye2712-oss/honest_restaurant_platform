from django.urls import path

from .views import RecalculateAIProfileView, RestaurantAIProfileView

urlpatterns = [
    path("restaurant/<int:pk>/profile/",     RestaurantAIProfileView.as_view(),    name="ai-profile"),
    path("restaurant/<int:pk>/recalculate/", RecalculateAIProfileView.as_view(),   name="ai-recalculate"),
]
