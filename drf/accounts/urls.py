from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # ── 템플릿 페이지 (GET 전용 — POST는 Axios가 아래 API 엔드포인트 직접 호출) ──
    path("signup/", TemplateView.as_view(template_name="accounts/signup.html"), name="signup"),
    path("login/",  TemplateView.as_view(template_name="accounts/login.html"),  name="login"),

    # ── Axios 전용 — 세션 + JWT 쿠키 동시 처리 ─────────────────────────────────
    # POST /accounts/api/ajax-login/   → 로그인  (세션 생성 + JWT 쿠키 발급)
    # POST /accounts/api/ajax-logout/  → 로그아웃 (세션 삭제 + JWT 블랙리스트 + 쿠키 삭제)
    # POST /accounts/api/ajax-signup/  → 회원가입 (유저 생성 + 세션 + JWT 쿠키)
    path("api/check-username/",  views.UsernameCheckView.as_view(), name="check-username"),
    path("api/ajax-login/",  views.AjaxLoginView.as_view(),  name="ajax-login"),
    path("api/ajax-logout/", views.AjaxLogoutView.as_view(), name="ajax-logout"),
    path("api/ajax-signup/", views.AjaxSignupView.as_view(), name="ajax-signup"),

    # ── JWT 전용 REST API (토큰 갱신 · 내 정보 조회) ───────────────────────────
    path("api/token/refresh/", views.APITokenRefreshView.as_view(), name="api-token-refresh"),
    path("api/me/",            views.MeView.as_view(),              name="api-me"),
    path("api/me/update/",     views.MeUpdateView.as_view(),        name="api-me-update"),

    # ── 마이페이지 ─────────────────────────────────────────────────────────────
    path("me/",                views.MyPageView.as_view(),          name="mypage"),

    # ── 소셜 로그인 (카카오 · 네이버) ──────────────────────────────────────────
    path("kakao/login/",     views.KakaoLoginView.as_view(),     name="kakao-login"),
    path("kakao/callback/",  views.KakaoCallbackView.as_view(),  name="kakao-callback"),
    path("naver/login/",     views.NaverLoginView.as_view(),     name="naver-login"),
    path("naver/callback/",  views.NaverCallbackView.as_view(),  name="naver-callback"),
]
