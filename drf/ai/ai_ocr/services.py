"""
ai.ai_ocr.services
==================
Gemini Vision을 이용해 영수증 이미지에서 주문 내역을 추출하고,
사장님이 직접 등록한 RestaurantMenuItem 가격과 비교한다.

주요 함수:
    analyze_receipt(verification_id)  — 영수증 분석 + 메뉴 가격 비교
"""

import json
import logging
import re

import PIL.Image

from django.conf import settings
from django.utils import timezone

from ai.utils import get_gemini_client

logger = logging.getLogger(__name__)

# 가격일치율 점수 기준 (레벨화 기준 정리.md)
_PRICE_SCORE_TABLE = [
    (1.00, 20),
    (0.95, 15),
    (0.90, 10),
]
_PRICE_MIN_SAMPLE = 30  # 표본 30건 미만이면 점수 미반영


def _load_image(image_field):
    """Django ImageField → PIL.Image 변환."""
    return PIL.Image.open(image_field.path)


def _parse_json_response(text: str) -> dict | list:
    """Gemini 응답에서 JSON 블록만 추출해 파싱한다."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    return json.loads(cleaned)


def _normalize(name: str) -> str:
    """메뉴명 비교용 정규화: 공백·특수문자 제거, 소문자화."""
    return re.sub(r"[\s\-_·•·]", "", name).lower()


# ── 가격 비교 로직 ──────────────────────────────────────────────────────────────

def _find_menu_price(item_name: str, menu_prices: dict) -> int | None:
    """
    영수증 항목명으로 사장님 등록 가격을 검색한다.
    1차: 정확 일치 / 2차: 정규화 후 일치 / 3차: 부분 문자열 포함
    """
    if item_name in menu_prices:
        return menu_prices[item_name]

    norm_item = _normalize(item_name)

    for menu_name, price in menu_prices.items():
        if _normalize(menu_name) == norm_item:
            return price

    for menu_name, price in menu_prices.items():
        norm_menu = _normalize(menu_name)
        if norm_item in norm_menu or norm_menu in norm_item:
            return price

    return None


def compare_prices(receipt_items: list, menu_prices: dict) -> dict:
    """
    영수증 항목과 사장님 등록 가격을 비교한다.

    반환:
        match_rate       : 0.0~1.0 일치율
        matched_count    : 일치 항목 수
        compared_count   : 비교 가능 항목 수
        discrepancies    : 불일치 항목 목록
    """
    discrepancies = []
    matched = 0
    compared = 0

    for item in receipt_items:
        menu_name     = item.get("menu", "")
        receipt_price = item.get("price", 0)
        menu_price    = _find_menu_price(menu_name, menu_prices)

        if menu_price is None:
            continue

        compared += 1
        if receipt_price <= menu_price:
            matched += 1
        else:
            discrepancies.append({
                "menu":          menu_name,
                "menu_price":    menu_price,
                "receipt_price": receipt_price,
                "diff":          receipt_price - menu_price,
            })

    match_rate = matched / compared if compared > 0 else 1.0

    return {
        "match_rate":     round(match_rate, 4),
        "matched_count":  matched,
        "compared_count": compared,
        "discrepancies":  discrepancies,
    }


def calc_price_score(match_rate: float, sample_count: int) -> int:
    """가격일치율 → 레벨화 점수 변환."""
    if sample_count < _PRICE_MIN_SAMPLE:
        return 0
    for threshold, score in _PRICE_SCORE_TABLE:
        if match_rate >= threshold:
            return score
    return 0


# ── 영수증 분석 ────────────────────────────────────────────────────────────────

def analyze_receipt(verification_id: int) -> None:
    """
    영수증 이미지를 OCR하고 사장님이 등록한 메뉴 가격과 비교한다.
    메뉴 항목이 없으면 OCR 결과만 저장하고 비교는 건너뛴다.
    """
    # honest_restaurant 앱이 ai_ocr.services를 참조(calc_price_score)하므로
    # 최상단 import 시 순환 import 발생 — 함수 호출 시점에 지연 import
    from honest_restaurant.models import ReceiptVerification, RestaurantMenuItem

    try:
        verification = ReceiptVerification.objects.select_related("restaurant").get(
            pk=verification_id
        )
    except ReceiptVerification.DoesNotExist:
        logger.error("analyze_receipt: verification_id=%s 없음", verification_id)
        return

    if not verification.receipt_image:
        logger.info("analyze_receipt: 이미지 없음 verification_id=%s", verification_id)
        return

    prompt = """이 이미지는 식당 영수증입니다.
주문한 메뉴와 단가를 JSON 배열로 추출해주세요.
반드시 다음 형식만 출력하세요: [{"menu": "메뉴명", "price": 단가(숫자)}, ...]
규칙:
- price는 1개당 단가 (수량 × 단가 아님)
- 소계·합계·세금·봉사료·할인·포인트는 제외
- 수량이 있으면 각 항목을 따로 적지 말고 단가만 기재
- JSON 외 다른 텍스트 출력 금지"""

    try:
        client   = get_gemini_client()
        image    = _load_image(verification.receipt_image)
        response = client.models.generate_content(
            model    = settings.GEMINI_MODEL,
            contents = [image, prompt],
        )
        items = _parse_json_response(response.text)
        if not isinstance(items, list):
            raise ValueError(f"예상치 못한 응답 형식: {type(items)}")

        items = [{"menu": str(i["menu"]), "price": int(i["price"])} for i in items]

        # 사장님이 등록한 메뉴 가격이 있으면 비교
        menu_qs = RestaurantMenuItem.objects.filter(
            restaurant_id=verification.restaurant_id
        ).values_list("name", "price")
        menu_prices = dict(menu_qs)

        if menu_prices:
            result = compare_prices(items, menu_prices)
            verification.price_match_rate    = result["match_rate"]
            verification.price_discrepancies = result["discrepancies"]
            logger.info(
                "영수증 가격 비교 완료 verification_id=%s 일치율=%.0f%% 불일치=%d건",
                verification_id,
                result["match_rate"] * 100,
                len(result["discrepancies"]),
            )
        else:
            verification.price_match_rate    = None
            verification.price_discrepancies = []
            logger.info(
                "영수증 OCR 완료 (메뉴 미등록으로 비교 생략) verification_id=%s",
                verification_id,
            )

        verification.extracted_items = items
        verification.ocr_analyzed_at = timezone.now()
        verification.save()

    except Exception as exc:
        logger.error("영수증 분석 실패 verification_id=%s: %s", verification_id, exc)
        raise
