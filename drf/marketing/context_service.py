"""
marketing.context_service
=========================
Gemini 마케팅 글 생성에 필요한 오늘의 컨텍스트를 수집한다.
    - 날씨   : Open-Meteo API (무료, API 키 불필요)
    - 기념일  : holidays 라이브러리 (로컬, API 호출 없음)
    - 뉴스    : Naver Search API

외부 API 장애 시 해당 항목을 빈 문자열로 처리하고 글 생성은 계속 진행한다.
결과는 6시간 캐싱 — 매 요청마다 외부 API를 호출하지 않는다.
"""

import datetime
import logging

import holidays
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_today_context(city: str = "Seoul") -> dict:
    """날씨 + 기념일 + 뉴스를 묶어 반환."""
    cache_key = f"mkt_context_{datetime.date.today()}_{city}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    ctx = {
        "weather":  _get_weather(city),
        "holidays": _get_holidays(),
        "news":     _get_news(),
    }
    cache.set(cache_key, ctx, timeout=60 * 60 * 6)
    return ctx


_CITY_COORDS = {
    "Seoul":   (37.5665, 126.9780),
    "Busan":   (35.1796, 129.0756),
    "Incheon": (37.4563, 126.7052),
    "Daegu":   (35.8714, 128.6014),
    "Daejeon": (36.3504, 127.3845),
    "Gwangju": (35.1595, 126.8526),
    "Suwon":   (37.2636, 127.0286),
}

_WMO_CODE = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "서리 안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈",
    80: "소나기", 81: "강한 소나기", 95: "뇌우",
}


def _get_weather(city: str = "Seoul") -> str:
    lat, lon = _CITY_COORDS.get(city, _CITY_COORDS["Seoul"])
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "current":   "temperature_2m,apparent_temperature,weathercode",
                "timezone":  "Asia/Seoul",
            },
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning("Open-Meteo 응답 오류: %s", resp.status_code)
            return ""
        current = resp.json().get("current", {})
        code   = current.get("weathercode", 0)
        temp   = round(current.get("temperature_2m", 0))
        feels  = round(current.get("apparent_temperature", 0))
        desc   = _WMO_CODE.get(code, "흐림")
        return f"{desc}, 기온 {temp}°C (체감 {feels}°C)"
    except Exception:
        logger.exception("날씨 수집 실패")
        return ""


def _get_holidays() -> str:
    """오늘 포함 3일 이내 한국 공휴일·기념일."""
    kr_holidays = holidays.KR()
    today = datetime.date.today()
    found = []
    for i in range(4):
        d = today + datetime.timedelta(days=i)
        if d in kr_holidays:
            label = "오늘" if i == 0 else f"{i}일 후"
            found.append(f"{label} {kr_holidays[d]}")
    return ", ".join(found) if found else ""


def _get_news() -> str:
    """Naver Search API — 외식·맛집 최신 뉴스 2건."""
    client_id     = getattr(settings, "NAVER_CLIENT_ID",     "")
    client_secret = getattr(settings, "NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return ""
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            params={"query": "외식 맛집 트렌드", "display": 2, "sort": "date"},
            headers={
                "X-Naver-Client-Id":     client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            timeout=5,
        )
        items = resp.json().get("items", [])
        return " / ".join(
            i["title"].replace("<b>", "").replace("</b>", "")
            for i in items
        )
    except Exception:
        logger.exception("뉴스 수집 실패")
        return ""
