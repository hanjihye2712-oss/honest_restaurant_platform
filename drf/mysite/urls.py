from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls.static import static

from interactions.urls import api_urlpatterns, page_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('honest_restaurant.urls')),
    path("accounts/", include("accounts.urls")),
    path("api/interactions/", include((api_urlpatterns, "interactions"), namespace="interactions")),
    path("marketing/",        include("marketing.urls", namespace="marketing")),
    path("",                  include(page_urlpatterns)),
    path('accounts/', include('allauth.urls')),
    path('sales/', include('sales.urls')),
    path("api/ai/", include("ai.ai_review_classifier.urls")),

    # 브라우저가 자동으로 요청하는 favicon.ico — 204로 응답해 404 제거
    path("favicon.ico", lambda request: HttpResponse(status=204)),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
