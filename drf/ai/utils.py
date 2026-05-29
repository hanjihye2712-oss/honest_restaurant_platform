"""
ai.utils
========
AI 앱 전반에서 공유하는 유틸리티.
"""

from django.conf import settings
from google import genai


def get_gemini_client() -> genai.Client:
    """설정된 API 키로 Gemini 클라이언트를 생성해 반환한다."""
    return genai.Client(api_key=settings.GEMINI_API_KEY)
