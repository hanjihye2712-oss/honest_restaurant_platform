import os
import requests
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as session_login, logout as session_logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ── 로그인 전용 스로틀 (5회/분) ───────────────────────────────────────────────
class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


# ── 쿠키 헬퍼 ────────────────────────────────────────────────────────────────
JWT = settings.SIMPLE_JWT

def _write_token_cookies(response: Response, access_str: str, refresh_str: str) -> None:
    """access/refresh 문자열을 HttpOnly 쿠키로 세팅하는 저수준 헬퍼."""
    _shared = dict(
        httponly=JWT["AUTH_COOKIE_HTTP_ONLY"],
        secure=JWT["AUTH_COOKIE_SECURE"],
        samesite=JWT["AUTH_COOKIE_SAMESITE"],
        path=JWT["AUTH_COOKIE_PATH"],
    )
    response.set_cookie(
        key=JWT["AUTH_COOKIE"],
        value=access_str,
        max_age=int(JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        **_shared,
    )
    response.set_cookie(
        key=JWT["AUTH_COOKIE_REFRESH"],
        value=refresh_str,
        max_age=int(JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        **_shared,
    )


def _set_token_cookies(response: Response, refresh: RefreshToken) -> None:
    _write_token_cookies(response, str(refresh.access_token), str(refresh))


def _clear_token_cookies(response: Response) -> None:
    _shared = dict(
        path=JWT["AUTH_COOKIE_PATH"],
        domain=JWT["AUTH_COOKIE_DOMAIN"],
        samesite=JWT["AUTH_COOKIE_SAMESITE"],
    )
    response.delete_cookie(JWT["AUTH_COOKIE"], **_shared)
    response.delete_cookie(JWT["AUTH_COOKIE_REFRESH"], **_shared)


# ══════════════════════════════════════════════════════════════════════════════
# JWT API 뷰
# ══════════════════════════════════════════════════════════════════════════════

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
        new_access_str  = serializer.validated_data["access"]

        response = Response({"detail": "토큰 갱신 완료"}, status=status.HTTP_200_OK)
        _write_token_cookies(response, new_access_str, new_refresh_str)
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


# ══════════════════════════════════════════════════════════════════════════════
# Axios(SPA) 전용 뷰 — 세션 + JWT 동시 처리
# ══════════════════════════════════════════════════════════════════════════════

class AjaxLoginView(APIView):
    """
    POST /accounts/api/ajax-login/
    Body: { "username": "...", "password": "...", "next": "/" }
    Django 세션 생성 + JWT 쿠키 발급
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"detail": "아이디와 비밀번호를 입력하세요."},
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

        session_login(request, user)

        next_url = request.data.get("next", "") or "/"
        refresh = RefreshToken.for_user(user)
        response = Response(
            {"detail": "로그인 성공", "redirect": next_url},
            status=status.HTTP_200_OK,
        )
        _set_token_cookies(response, refresh)
        return response


class AjaxSignupView(APIView):
    """
    POST /accounts/api/ajax-signup/
    Body: { "username": "...", "password1": "...", "password2": "..." }
    유저 생성 + 세션 생성 + JWT 쿠키 발급
    """
    permission_classes = [AllowAny]

    def post(self, request):
        form = UserCreationForm(request.data)
        if form.is_valid():
            user = form.save()
            session_login(
                request, user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            refresh = RefreshToken.for_user(user)
            response = Response(
                {"detail": "가입 완료", "redirect": "/"},
                status=status.HTTP_201_CREATED,
            )
            _set_token_cookies(response, refresh)
            return response
        return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)


class AjaxLogoutView(APIView):
    """
    POST /accounts/api/ajax-logout/
    Django 세션 삭제 + refresh 블랙리스트 + JWT 쿠키 삭제
    """
    permission_classes = [AllowAny]

    def post(self, request):
        session_logout(request._request)   # DRF Request → 원본 Django WSGIRequest

        raw_refresh = request.COOKIES.get(JWT["AUTH_COOKIE_REFRESH"])
        response = Response({"detail": "로그아웃 완료"}, status=status.HTTP_200_OK)
        _clear_token_cookies(response)

        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                token.blacklist()
            except TokenError:
                pass

        return response


# ══════════════════════════════════════════════════════════════════════════════
# 소셜 로그인 뷰 (카카오, 네이버)
# ══════════════════════════════════════════════════════════════════════════════

class KakaoLoginView(APIView):
    """
    GET /accounts/kakao/login/
    카카오 OAuth2 인가 페이지로 리다이렉트
    """
    permission_classes = [AllowAny]

    def get(self, request):
        kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
        redirect_uri = os.getenv("KAKAO_REDIRECT_URI")

        kakao_auth_url = (
            "https://kauth.kakao.com/oauth/authorize"
            f"?response_type=code"
            f"&client_id={kakao_rest_api_key}"
            f"&redirect_uri={redirect_uri}"
        )

        return redirect(kakao_auth_url)


class KakaoCallbackView(APIView):
    """
    GET /accounts/kakao/callback/
    카카오 OAuth2 콜백 처리 (인가 코드 → 토큰 → 사용자 정보)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get("code")

        if not code:
            return Response({"error": "인가 코드가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
        kakao_client_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
        redirect_uri = os.getenv("KAKAO_REDIRECT_URI")

        token_url = "https://kauth.kakao.com/oauth/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": kakao_rest_api_key,
            "redirect_uri": redirect_uri,
            "code": code,
        }

        if kakao_client_secret:
            token_data["client_secret"] = kakao_client_secret

        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        kakao_access_token = token_json.get("access_token")

        if not kakao_access_token:
            return Response({
                "error": "카카오 access_token 발급 실패",
                "detail": token_json
            }, status=status.HTTP_400_BAD_REQUEST)

        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {"Authorization": f"Bearer {kakao_access_token}"}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()

        kakao_id = user_info.get("id")
        kakao_account = user_info.get("kakao_account", {})
        email = kakao_account.get("email")
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname") or kakao_account.get("name") or ""

        if not kakao_id:
            return Response({"error": "카카오 사용자 정보 조회 실패"}, status=status.HTTP_400_BAD_REQUEST)

        username = f"kakao_{kakao_id}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email or "",
                "first_name": nickname or "",
            }
        )

        if not created:
            user.email = email or user.email
            user.first_name = nickname or user.first_name
            user.save()

        session_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        refresh = RefreshToken.for_user(user)
        response = redirect("/")
        _set_token_cookies(response, refresh)
        return response


class NaverLoginView(APIView):
    """
    GET /accounts/naver/login/
    네이버 OAuth2 인가 페이지로 리다이렉트
    """
    permission_classes = [AllowAny]

    def get(self, request):
        naver_client_id = os.getenv("NAVER_CLIENT_ID")
        redirect_uri = os.getenv("NAVER_REDIRECT_URI")
        state = os.urandom(16).hex()
        request.session['naver_state'] = state

        naver_auth_url = (
            "https://nid.naver.com/oauth2.0/authorize"
            f"?response_type=code"
            f"&client_id={naver_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )

        return redirect(naver_auth_url)


class NaverCallbackView(APIView):
    """
    GET /accounts/naver/callback/
    네이버 OAuth2 콜백 처리 (인가 코드 → 토큰 → 사용자 정보)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code:
            return Response({"error": "인가 코드가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        session_state = request.session.get('naver_state')
        if state != session_state:
            return Response({"error": "state 검증 실패"}, status=status.HTTP_400_BAD_REQUEST)

        naver_client_id = os.getenv("NAVER_CLIENT_ID")
        naver_client_secret = os.getenv("NAVER_CLIENT_SECRET")
        redirect_uri = os.getenv("NAVER_REDIRECT_URI")

        token_url = "https://nid.naver.com/oauth2.0/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": naver_client_id,
            "client_secret": naver_client_secret,
            "code": code,
            "state": state,
        }

        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        naver_access_token = token_json.get("access_token")

        if not naver_access_token:
            return Response({
                "error": "네이버 access_token 발급 실패",
                "detail": token_json
            }, status=status.HTTP_400_BAD_REQUEST)

        user_info_url = "https://openapi.naver.com/v1/nid/me"
        headers = {"Authorization": f"Bearer {naver_access_token}"}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info_data = user_info_response.json()

        if user_info_data.get("resultcode") != "00":
            return Response({"error": "네이버 사용자 정보 조회 실패"}, status=status.HTTP_400_BAD_REQUEST)

        response_data = user_info_data.get("response", {})
        naver_id = response_data.get("id")
        email = response_data.get("email")
        nickname = response_data.get("nickname") or response_data.get("name") or ""

        if not naver_id:
            return Response({"error": "네이버 사용자 ID 없음"}, status=status.HTTP_400_BAD_REQUEST)

        username = f"naver_{naver_id}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email or "",
                "first_name": nickname or "",
            }
        )

        if not created:
            user.email = email or user.email
            user.first_name = nickname or user.first_name
            user.save()

        session_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        refresh = RefreshToken.for_user(user)
        response = redirect("/")
        _set_token_cookies(response, refresh)
        return response
