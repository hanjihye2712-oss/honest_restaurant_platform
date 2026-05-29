from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    path('',             views.DashboardView.as_view(),         name='dashboard'),
    path('restaurants/', views.RestaurantManageView.as_view(),  name='restaurants'),
    path('users/',       views.UserManageView.as_view(),        name='users'),
    path('receipts/',    views.ReceiptManageView.as_view(),     name='receipts'),
    path('ai/',          views.AIManageView.as_view(),          name='ai'),
    path('marketing/',   views.MarketingManageView.as_view(),   name='marketing'),
]
