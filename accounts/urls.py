from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ── 기존 템플릿 기반 뷰 (HTML 페이지) ──────────────────────────────────
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # ── JWT API 엔드포인트 (JSON) ───────────────────────────────────────────
    # POST  /api/accounts/login/          → 로그인 (JWT 쿠키 발급)
    # POST  /api/accounts/logout/         → 로그아웃 (refresh 블랙리스트 + 쿠키 삭제)
    # POST  /api/accounts/token/refresh/  → access 토큰 갱신
    # GET   /api/accounts/me/             → 내 정보 조회
    path("api/login/", views.APILoginView.as_view(), name="api-login"),
    path("api/logout/", views.APILogoutView.as_view(), name="api-logout"),
    path("api/token/refresh/", views.APITokenRefreshView.as_view(), name="api-token-refresh"),
    path("api/me/", views.MeView.as_view(), name="api-me"),
]
