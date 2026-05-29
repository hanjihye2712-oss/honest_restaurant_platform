from django.urls import path

from .views import AIReportHistoryView, GenerateAIReportView, RestaurantAIReportView

urlpatterns = [
    path("restaurant/<int:pk>/report/",          RestaurantAIReportView.as_view(),  name="ai-report"),
    path("restaurant/<int:pk>/report/generate/", GenerateAIReportView.as_view(),    name="ai-report-generate"),
    path("reports/history/",                     AIReportHistoryView.as_view(),     name="ai-report-history"),
]
