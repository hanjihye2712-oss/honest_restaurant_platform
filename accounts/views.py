from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken


# ── 로그인 전용 스로틀 (5회/분) ───────────────────────────────────────────────
class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


# ── 쿠키 헬퍼 ────────────────────────────────────────────────────────────────
JWT = settings.SIMPLE_JWT

def _set_token_cookies(response: Response, refresh: RefreshToken) -> None:
    access_max_age = int(JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    refresh_max_age = int(JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

    response.set_cookie(
        key=JWT["AUTH_COOKIE"],
        value=str(refresh.access_token),
        max_age=access_max_age,
        httponly=JWT["AUTH_COOKIE_HTTP_ONLY"],
        secure=JWT["AUTH_COOKIE_SECURE"],
        samesite=JWT["AUTH_COOKIE_SAMESITE"],
        path=JWT["AUTH_COOKIE_PATH"],
    )
    response.set_cookie(
        key=JWT["AUTH_COOKIE_REFRESH"],
        value=str(refresh),
        max_age=refresh_max_age,
        httponly=JWT["AUTH_COOKIE_HTTP_ONLY"],
        secure=JWT["AUTH_COOKIE_SECURE"],
        samesite=JWT["AUTH_COOKIE_SAMESITE"],
        path=JWT["AUTH_COOKIE_PATH"],
    )


def _clear_token_cookies(response: Response) -> None:
    response.delete_cookie(JWT["AUTH_COOKIE"], path=JWT["AUTH_COOKIE_PATH"])
    response.delete_cookie(JWT["AUTH_COOKIE_REFRESH"], path=JWT["AUTH_COOKIE_PATH"])


# ── 기존 템플릿 기반 회원가입 뷰 (유지) ──────────────────────────────────────
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("login"))
    else:
        form = UserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})


# ══════════════════════════════════════════════════════════════════════════════
# JWT API 뷰
# ══════════════════════════════════════════════════════════════════════════════

class APILoginView(APIView):
    """
    POST /api/accounts/login/
    Body: { "username": "...", "password": "..." }
    성공: access/refresh 토큰을 HttpOnly 쿠키에 담아 반환
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"detail": "username과 password를 입력하세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "비활성화된 계정입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "detail": "로그인 성공",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "is_staff": user.is_staff,
                },
            },
            status=status.HTTP_200_OK,
        )
        _set_token_cookies(response, refresh)
        return response


class APILogoutView(APIView):
    """
    POST /api/accounts/logout/
    쿠키의 refresh 토큰을 블랙리스트에 등록하고 쿠키 삭제.
    인증 없이도 호출 가능 (이미 만료된 경우 등).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(JWT["AUTH_COOKIE_REFRESH"])
        response = Response({"detail": "로그아웃 완료"}, status=status.HTTP_200_OK)
        _clear_token_cookies(response)

        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                token.blacklist()
            except TokenError:
                pass  # 이미 만료·블랙리스트된 토큰은 무시

        return response


class APITokenRefreshView(APIView):
    """
    POST /api/accounts/token/refresh/
    쿠키의 refresh 토큰으로 새 access 토큰 발급.
    ROTATE_REFRESH_TOKENS=True이므로 refresh 토큰도 교체됨.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(JWT["AUTH_COOKIE_REFRESH"])
        if not raw_refresh:
            return Response(
                {"detail": "refresh 토큰이 없습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        # ROTATE_REFRESH_TOKENS=True → serializer가 새 refresh 토큰 반환
        new_refresh_str = serializer.validated_data.get("refresh", raw_refresh)
        new_access_str = serializer.validated_data["access"]

        response = Response({"detail": "토큰 갱신 완료"}, status=status.HTTP_200_OK)
        access_max_age = int(JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        refresh_max_age = int(JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

        response.set_cookie(
            key=JWT["AUTH_COOKIE"],
            value=new_access_str,
            max_age=access_max_age,
            httponly=JWT["AUTH_COOKIE_HTTP_ONLY"],
            secure=JWT["AUTH_COOKIE_SECURE"],
            samesite=JWT["AUTH_COOKIE_SAMESITE"],
            path=JWT["AUTH_COOKIE_PATH"],
        )
        response.set_cookie(
            key=JWT["AUTH_COOKIE_REFRESH"],
            value=new_refresh_str,
            max_age=refresh_max_age,
            httponly=JWT["AUTH_COOKIE_HTTP_ONLY"],
            secure=JWT["AUTH_COOKIE_SECURE"],
            samesite=JWT["AUTH_COOKIE_SAMESITE"],
            path=JWT["AUTH_COOKIE_PATH"],
        )
        return response


class MeView(APIView):
    """
    GET /api/accounts/me/
    현재 로그인한 사용자 정보 반환.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_staff": user.is_staff,
                "date_joined": user.date_joined,
            }
        )
