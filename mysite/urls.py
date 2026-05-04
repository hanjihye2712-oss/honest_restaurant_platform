from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('honest_restaurant/', include('honest_restaurant.urls')),  # API 엔드포인트 추가
]
