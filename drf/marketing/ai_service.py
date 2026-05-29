"""
marketing.ai_service
====================
Gemini API를 호출해 마케팅 글(본문 + 해시태그)을 생성한다.
플랫폼별 문체·길이·이모지 사용 여부는 DB(MarketingPlatformConfig)에서 읽는다.
AI 모델·프롬프트 설정은 DB(MarketingAIConfig)에서 읽는다.
설정값은 5분 캐시로 DB 부하를 줄인다.
"""

import json
import logging

from django.core.cache import cache

from ai.utils import get_gemini_client

logger = logging.getLogger(__name__)

# 하드코딩 폴백 — DB에 레코드가 없을 경우에만 사용
_GUIDE_FALLBACK = {
    "instagram":   "짧고 감성적, 이모지 포함, 해시태그 5~8개",
    "naver_blog":  "500자 이상, 친절한 설명체, 해시태그 3~5개",
    "facebook":    "자연스러운 구어체, 해시태그 2~3개",
    "kakao_story": "짧고 친근하게 2~3줄, 이모지 포함",
}


def _get_platform_configs() -> dict:
    """활성 플랫폼 설정을 {platform: {display_name, guide}} 형태로 반환 (5분 캐시)."""
    cached = cache.get('mkt_platform_configs')
    if cached is not None:
        return cached
    from .models import MarketingPlatformConfig
    configs = {
        c.platform: {'display_name': c.display_name, 'guide': c.guide}
        for c in MarketingPlatformConfig.objects.filter(is_active=True).order_by('order')
    }
    cache.set('mkt_platform_configs', configs, timeout=300)
    return configs


def _get_ai_config() -> dict:
    """AI 생성 설정을 dict로 반환 (5분 캐시)."""
    cached = cache.get('mkt_ai_config')
    if cached is not None:
        return cached
    from .models import MarketingAIConfig
    cfg = MarketingAIConfig.get_config()
    data = {
        'model_name':          cfg.model_name,
        'temperature':         cfg.temperature,
        'role_description':    cfg.role_description,
        'writing_instruction': cfg.writing_instruction,
    }
    cache.set('mkt_ai_config', data, timeout=300)
    return data


def get_active_platforms() -> list[dict]:
    """활성 플랫폼 목록을 [{platform, display_name}] 형태로 반환."""
    configs = _get_platform_configs()
    return [{'platform': k, 'display_name': v['display_name']} for k, v in configs.items()]


def generate_marketing_content(
    restaurant,
    keywords: str,
    platform: str,
    context: dict,
) -> dict:
    """
    Gemini에게 마케팅 글 생성 요청.
    반환: {"content": str, "hashtags": list[str]}
    """
    context_str = _build_context_str(context)
    prompt      = _build_prompt(restaurant, keywords, platform, context_str)
    ai_cfg      = _get_ai_config()

    client   = get_gemini_client()
    response = client.models.generate_content(
        model=ai_cfg['model_name'],
        contents=prompt,
        config={'temperature': ai_cfg['temperature']},
    )

    return _parse_response(response.text)


def _build_context_str(context: dict) -> str:
    parts = []
    if context.get("weather"):
        parts.append(f"오늘 날씨: {context['weather']}")
    if context.get("holidays"):
        parts.append(f"기념일·공휴일: {context['holidays']}")
    if context.get("news"):
        parts.append(f"오늘의 외식 트렌드 뉴스: {context['news']}")
    return "\n".join(parts) if parts else "특별한 이벤트 없음"


def _build_prompt(restaurant, keywords: str, platform: str, context_str: str) -> str:
    platform_configs = _get_platform_configs()
    ai_cfg           = _get_ai_config()

    platform_info = platform_configs.get(platform, {})
    guide         = platform_info.get('guide') or _GUIDE_FALLBACK.get(platform, '')

    role        = ai_cfg['role_description']
    instruction = ai_cfg['writing_instruction'].format(platform=platform)

    return f"""{role}

[식당 정보]
- 식당명: {restaurant.name}
- 업종: {restaurant.business_type or "음식점"}
- 지역: {getattr(restaurant, 'province', '') or ""} {getattr(restaurant, 'city', '') or ""}

[오늘의 상황]
{context_str}

[사장님의 요청 / 강조하고 싶은 내용]
{keywords}

[발행 플랫폼 · 작성 가이드]
{platform} — {guide}

{instruction}

반드시 아래 JSON 형식으로만 답변하세요. 다른 텍스트는 절대 포함하지 마세요:
{{
  "content": "본문 내용",
  "hashtags": ["해시태그1", "해시태그2"]
}}"""


def _parse_response(text: str) -> dict:
    """Gemini 응답에서 JSON 추출 — ```json ... ``` 블록 처리."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except (json.JSONDecodeError, ValueError):
                continue

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.error("Gemini 응답 파싱 실패: %s", text[:200])
        raise ValueError("AI 응답을 파싱할 수 없습니다. 다시 시도해주세요.")
