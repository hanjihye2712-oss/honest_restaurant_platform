"""
sales.urls
==========
    /sales/checkout/          — 결제 페이지
    /sales/success/           — 결제 성공 (Toss 콜백)
    /sales/fail/              — 결제 실패 (Toss 콜백)
    /sales/webhook/           — Toss 웹훅 수신
    /sales/api/create-order/  — 결제 전 주문 미리 저장
    /sales/detail/            — 전체 매출 상세
    /sales/detail/<slug>/     — 메뉴별 상세
"""
from django.urls import path

from .views import (
    CheckoutView,
    CreateOrderAPIView,
    FailView,
    RegisterManagedRestaurantView,
    SalesDashboardAPIView,
    SalesDetailView,
    SuccessView,
    TossWebhookView,
)

app_name = 'sales'

urlpatterns = [
    path('checkout/',         CheckoutView.as_view(),        name='checkout'),
    path('success/',          SuccessView.as_view(),          name='success'),
    path('fail/',             FailView.as_view(),             name='fail'),
    path('webhook/',          TossWebhookView.as_view(),      name='toss_webhook'),
    path('api/create-order/', CreateOrderAPIView.as_view(),   name='create_order_api'),
    path('api/dashboard/',    SalesDashboardAPIView.as_view(), name='dashboard_api'),
    path('api/register-restaurant/<int:pk>/', RegisterManagedRestaurantView.as_view(), name='register_restaurant'),
    path('detail/',           SalesDetailView.as_view(),      name='detail_overview'),
    path('detail/<slug:slug>/', SalesDetailView.as_view(),    name='detail'),
]
