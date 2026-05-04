import logging
import requests
from datetime import datetime

from django.conf import settings

from honest_restaurant.models import PublicRestaurantData

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────
SEOUL_API_BASE    = "http://openapi.seoul.go.kr:8088"
SERVICE_NAME      = "LOCALDATA_072404"   # 서울시 일반음식점 인허가 정보
BATCH_SIZE        = 1000                 # API 1회 최대 허용 건수
SUCCESS_CODE      = "INFO-000"           # 정상 응답 코드


# ─────────────────────────────────────────────────────
# API 필드명 ↔ 모델 필드명 매핑 테이블
#
# 서울 열린데이터광장 OA-16094 실제 응답 키 기준
# (스크린샷 출력항목 39개 중 정직식당에 필요한 항목만 추출)
# ─────────────────────────────────────────────────────
FIELD_MAP = {
    # API 응답 키          : 모델 필드명
    "MGTNO"              : "management_no",         # 관리번호 (unique 식별자)
    "BPLCNM"             : "name",                  # 업소명
    "SITEWHLADDR"        : "address_jibun",         # 소재지전체주소 (지번)
    "RDNWHLADDR"         : "address_road",          # 도로명전체주소
    "RDNPOSTNO"          : "_rdnpostno",            # 도로명우편번호 → 자치구 파싱용 (저장 X)
    "SITETEL"            : "phone",                 # 소재지전화
    "UPTAENM"            : "business_type",         # 업태구분명
    "DTLSTATENM"         : "category_name",         # 상세영업상태명 (업종명 역할)
    "SANITTNBIZNM"       : "sanitation_business_type",  # 위생업태명
    "APVPERMYMD"         : "license_date",          # 인허가일자
    "APVCANCELYMD"       : "license_cancel_date",   # 인허가취소일자
    "TRDSTATEGBN"        : "status_code",           # 영업상태구분코드 (01:영업 02:휴업 03:폐업)
    "SITEAREA"           : "area",                  # 소재지면적
    "LASTMODTS"          : "last_modified_at",      # 최종수정시점
    "X"                  : "longitude",             # 경도 (중부원점TM — WGS84 아님, 추후 변환 필요)
    "Y"                  : "latitude",              # 위도 (중부원점TM — WGS84 아님, 추후 변환 필요)
}

# 자치구 추출에 사용할 서울시 25개 자치구 목록
SEOUL_DISTRICTS = [
    "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
    "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구",
    "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구",
    "강동구",
]


# ─────────────────────────────────────────────────────
# 파싱 헬퍼 함수
# ─────────────────────────────────────────────────────

def _parse_date(val: str | None):
    """'20230115' → date(2023, 1, 15), 빈값 → None"""
    if not val or not val.strip():
        return None
    try:
        return datetime.strptime(val.strip(), "%Y%m%d").date()
    except ValueError:
        return None


def _parse_datetime(val: str | None):
    """'20230115123045' → datetime(2023,1,15,12,30,45), 빈값 → None"""
    if not val or not val.strip():
        return None
    try:
        return datetime.strptime(val.strip()[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _parse_float(val: str | None):
    """'127.023' → 127.023, 빈값 → None"""
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


def _extract_district(address: str | None) -> str:
    """
    도로명/지번 주소에서 자치구 추출
    예) '서울특별시 종로구 익선동 ...' → '종로구'
    """
    if not address:
        return ""
    for district in SEOUL_DISTRICTS:
        if district in address:
            return district
    return ""


# ─────────────────────────────────────────────────────
# API 호출 함수
# ─────────────────────────────────────────────────────

def fetch_restaurants(start: int, end: int) -> list[dict]:
    """
    서울 열린데이터광장에서 start~end 번째 데이터를 가져옴

    URL 형식:
        http://openapi.seoul.go.kr:8088/{KEY}/json/LOCALDATA_072404/{start}/{end}/

    Returns:
        row 리스트 (비어있으면 [])
    """
    api_key = settings.SEOUL_API_KEY
    url = f"{SEOUL_API_BASE}/{api_key}/json/{SERVICE_NAME}/{start}/{end}/"

    logger.info(f"[SeoulAPI] 호출: {start}~{end}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        logger.error(f"[SeoulAPI] 타임아웃 ({start}~{end})")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"[SeoulAPI] 요청 실패: {e}")
        return []
    except ValueError:
        logger.error(f"[SeoulAPI] JSON 파싱 실패 ({start}~{end})")
        return []

    # 응답 구조: { "LOCALDATA_072404": { "RESULT": {...}, "list_total_count": N, "row": [...] } }
    service_data = data.get(SERVICE_NAME, {})
    result       = service_data.get("RESULT", {})
    result_code  = result.get("CODE", "")

    if result_code != SUCCESS_CODE:
        logger.warning(f"[SeoulAPI] 응답 코드: {result_code} / 메시지: {result.get('MESSAGE', '')}")
        return []

    rows = service_data.get("row", [])
    logger.info(f"[SeoulAPI] {len(rows)}건 수신 완료")
    return rows


# ─────────────────────────────────────────────────────
# DB 저장 함수
# ─────────────────────────────────────────────────────

def _row_to_defaults(row: dict) -> dict:
    """
    API 응답 row 1건을 모델 defaults dict으로 변환
    """
    address_road   = row.get("RDNWHLADDR", "").strip()
    address_jibun  = row.get("SITEWHLADDR", "").strip()

    # 자치구: 도로명 주소 우선, 없으면 지번 주소에서 파싱
    district = _extract_district(address_road) or _extract_district(address_jibun)

    return {
        "name"                    : row.get("BPLCNM", "").strip(),
        "address_road"            : address_road,
        "address_jibun"           : address_jibun,
        "district"                : district,
        "phone"                   : row.get("SITETEL", "").strip(),
        "business_type"           : row.get("UPTAENM", "").strip(),
        "category_name"           : row.get("DTLSTATENM", "").strip(),
        "sanitation_business_type": row.get("SANITTNBIZNM", "").strip(),
        "license_date"            : _parse_date(row.get("APVPERMYMD")),
        "license_cancel_date"     : _parse_date(row.get("APVCANCELYMD")),
        "status_code"             : row.get("TRDSTATEGBN", "").strip(),
        "area"                    : _parse_float(row.get("SITEAREA")),
        "last_modified_at"        : _parse_datetime(row.get("LASTMODTS")),
        # 주의: X/Y는 중부원점TM 좌표계 (WGS84 위경도 아님)
        # 지도 표시 시 좌표 변환 필요 (pyproj 등 사용)
        "longitude"               : _parse_float(row.get("X")),
        "latitude"                : _parse_float(row.get("Y")),
    }


def save_restaurants(rows: list[dict]) -> tuple[int, int]:
    """
    rows를 파싱해 DB에 upsert 저장 (update_or_create)

    Returns:
        (created_count, updated_count)
    """
    created_count = 0
    updated_count = 0
    skip_count    = 0

    for row in rows:
        management_no = row.get("MGTNO", "").strip()

        if not management_no:
            skip_count += 1
            continue  # 관리번호 없는 데이터는 스킵

        defaults = _row_to_defaults(row)

        try:
            _, created = PublicRestaurantData.objects.update_or_create(
                management_no=management_no,
                defaults=defaults,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        except Exception as e:
            logger.error(f"[SeoulAPI] DB 저장 실패 (MGTNO={management_no}): {e}")
            continue

    logger.info(
        f"[SeoulAPI] 저장 완료 — 신규: {created_count}건 / 갱신: {updated_count}건 / 스킵: {skip_count}건"
    )
    return created_count, updated_count