from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authorization 헤더 대신 HttpOnly 쿠키에서 Access Token을 읽는 인증 클래스.
    헤더에 토큰이 있으면 헤더를 우선한다 (API 테스트 편의).
    """

    def authenticate(self, request):
        # 헤더 우선 (Swagger, Postman 등 테스트용)
        header = self.get_header(request)
        if header:
            return super().authenticate(request)

        # 쿠키에서 access token 읽기
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None

        return self.get_user(validated_token), validated_token
