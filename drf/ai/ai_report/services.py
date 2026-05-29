"""
ai.ai_report.services
======================
Gemini API를 호출해 식당 AI 리포트를 생성한다.
모델명·Temperature·프롬프트는 AIReportConfig(DB)에서 읽는다.

흐름:
    1. RestaurantAIProfile 조회 (집계 데이터)
    2. AIReportConfig 조회 (설정)
    3. 프롬프트 구성
    4. Gemini API 호출
    5. RestaurantAIReport 저장
"""

import logging
from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone

from ai.utils import get_gemini_client

logger = logging.getLogger(__name__)


def _get_report_config() -> dict:
    """AI 리포트 설정을 dict로 반환 (5분 캐시)."""
    cached = cache.get('ai_report_config')
    if cached is not None:
        return cached
    from .models import AIReportConfig
    cfg = AIReportConfig.get_config()
    data = {
        'model_name':         cfg.model_name,
        'temperature':        cfg.temperature,
        'report_period_days': cfg.report_period_days,
        'role_description':   cfg.role_description,
        'writing_rules':      cfg.writing_rules,
    }
    cache.set('ai_report_config', data, timeout=300)
    return data


def _build_prompt(restaurant, profile) -> str:
    """RestaurantAIProfile 데이터를 기반으로 Gemini 프롬프트를 구성한다."""
    cfg = _get_report_config()

    pos_tags = ", ".join(
        f"{tag}({cnt}건)" for tag, cnt in list(profile.top_positive_tags.items())[:5]
    ) or "없음"
    neg_tags = ", ".join(
        f"{tag}({cnt}건)" for tag, cnt in list(profile.top_negative_tags.items())[:5]
    ) or "없음"

    hygiene_line = (
        f"⚠️ 위생 관련 부정 언급이 최근 14일간 {profile.recent_hygiene_negative_ratio:.0%}로 높습니다."
        if profile.hygiene_alert else ""
    )
    alley_line = (
        "🍀 골목장인 배지 자격 조건을 충족하고 있습니다."
        if profile.is_alley_eligible else ""
    )

    period_days   = cfg['report_period_days']
    role          = cfg['role_description'].format(period_days=period_days)
    writing_rules = cfg['writing_rules']

    return f"""{role}

[식당 정보]
- 식당명: {restaurant.name}
- 업종: {restaurant.business_type or "음식점"}
- 영업 기간: {restaurant.operating_years or "정보 없음"}년
{alley_line}

[리뷰 분석 데이터 (최근 {period_days}일)]
- 긍정 리뷰 비율: {profile.positive_ratio:.0%}
- 부정 리뷰 비율: {profile.negative_ratio:.0%}
- AI 점수: {profile.ai_net_score:+d}점 (보너스 {profile.ai_score_bonus:+d} / 패널티 {profile.ai_score_penalty:+d})
- 분석된 리뷰 수: {profile.review_count_analyzed}건
- 주요 긍정 키워드: {pos_tags}
- 주요 부정 키워드: {neg_tags}
{hygiene_line}

[작성 규칙]
{writing_rules}

[리포트 본문]을 작성한 뒤,
줄바꿈 후 [푸시 알림]으로 2줄 이내 요약 메시지도 작성해주세요.

형식:
[리포트 본문]
(3~4문장 본문)

[푸시 알림]
(2줄 이내 요약)"""


def generate_report(restaurant_id: int) -> None:
    """
    식당 AI 리포트를 생성하고 RestaurantAIReport에 저장한다.
    RestaurantAIProfile이 없으면 조용히 종료한다.
    """
    # ai_report·ai_review_classifier·honest_restaurant 세 앱이 서로 참조하므로
    # 최상단 import 시 순환 import 발생 — 함수 진입 시점에 지연 import
    from honest_restaurant.models import PublicRestaurantData
    from ai.ai_review_classifier.models import RestaurantAIProfile
    from .models import RestaurantAIReport

    try:
        restaurant = PublicRestaurantData.objects.get(pk=restaurant_id)
        profile    = restaurant.ai_profile
    except PublicRestaurantData.DoesNotExist:
        logger.error("generate_report: 식당을 찾을 수 없음 restaurant_id=%s", restaurant_id)
        return
    except RestaurantAIProfile.DoesNotExist:
        logger.info("generate_report: AI 프로필 없음 restaurant_id=%s, 건너뜀", restaurant_id)
        return

    cfg          = _get_report_config()
    period_days  = cfg['report_period_days']
    today        = date.today()
    period_start = today - timedelta(days=period_days)

    report = RestaurantAIReport.objects.create(
        restaurant   = restaurant,
        period_start = period_start,
        period_end   = today,
        status       = RestaurantAIReport.STATUS_PENDING,
    )

    try:
        client   = get_gemini_client()
        prompt   = _build_prompt(restaurant, profile)
        response = client.models.generate_content(
            model    = cfg['model_name'],
            contents = prompt,
            config   = {'temperature': cfg['temperature']},
        )
        raw = response.text.strip()

        report_text  = raw
        push_message = ""

        if "[푸시 알림]" in raw:
            parts        = raw.split("[푸시 알림]")
            report_text  = parts[0].replace("[리포트 본문]", "").strip()
            push_message = parts[1].strip()

        report.report_text  = report_text
        report.push_message = push_message
        report.status       = RestaurantAIReport.STATUS_DONE
        report.generated_at = timezone.now()
        report.error_msg    = ""
        report.save()

        logger.info(
            "AI 리포트 생성 완료 restaurant_id=%s period=%s~%s",
            restaurant_id, period_start, today,
        )

    except Exception as exc:
        logger.error("AI 리포트 생성 실패 restaurant_id=%s: %s", restaurant_id, exc, exc_info=True)
        report.status    = RestaurantAIReport.STATUS_FAILED
        report.error_msg = "리포트 생성 중 오류가 발생했습니다."
        report.save()
        raise
