"""
honest_restaurant.services
==========================
외부 API 동기화 서비스 클래스 모음.
HTTP 뷰 레이어와 완전히 분리하여 management commands에서만 호출한다.

    NationalRestaurantSyncer  — 행정안전부 전국 일반음식점 공공 API
    HygieneGradeSyncer        — 식품안전나라 C004 위생등급 API
    ExcellentRestaurantSyncer — 행정안전부 모범음식점 API
    AnsimRestaurantSyncer     — 농림축산식품부 안심식당 API
    GoodPriceShopSyncer       — 행정안전부 착한가격업소 API
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from django.conf import settings
from django.db.models import Q
from pyproj import Transformer as _GeoTransformer

from .models import PublicRestaurantData

# ── 좌표 변환기 (모듈 레벨 싱글턴) ──────────────────────────────
_TM_TO_WGS84 = _GeoTransformer.from_crs('EPSG:5174', 'EPSG:4326', always_xy=True)

# ── 시/도 코드 → 명칭 매핑 (공통 상수) ──────────────────────────
PROVINCE_CODE_MAP = {
    "11": "서울특별시", "26": "부산광역시", "27": "대구광역시",
    "28": "인천광역시", "29": "광주광역시", "30": "대전광역시",
    "31": "울산광역시", "36": "세종특별자치시",
    "41": "경기도",    "42": "강원특별자치도",
    "43": "충청북도",  "44": "충청남도",
    "45": "전북특별자치도",
    "46": "전라남도",  "47": "경상북도", "48": "경상남도",
    "50": "제주특별자치도",
}

# 주소 앞부분 매칭 시 사용할 접두사 길이
_ADDR_PREFIX_LEN = 20


# ── 공통 유틸 함수 ────────────────────────────────────────────────

def parse_date(val) -> "datetime.date | None":
    """
    날짜 문자열 → date 객체.
    YYYYMMDD 및 YYYY-MM-DD 두 형식 모두 지원.
    파싱 불가 시 None 반환.
    """
    if not val:
        return None
    val = str(val).strip()
    if not val:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def address_prefix_q(addr: str, prefix_len: int = _ADDR_PREFIX_LEN) -> Q:
    """주소 앞 prefix_len자로 road/jibun 양쪽을 OR 필터하는 Q 객체 반환."""
    prefix = addr[:prefix_len]
    return Q(address_road__startswith=prefix) | Q(address_jibun__startswith=prefix)


def convert_tm_to_wgs84(x_str, y_str) -> "tuple[float | None, float | None]":
    """
    중부원점TM (EPSG:5174) → WGS84 (EPSG:4326).
    반환: (latitude, longitude) 또는 (None, None)
    """
    try:
        x = float(x_str) if x_str else None
        y = float(y_str) if y_str else None
        if x is None or y is None:
            return None, None
        lng, lat = _TM_TO_WGS84.transform(x, y)
        return lat, lng
    except (ValueError, TypeError):
        return None, None


# ══════════════════════════════════════════════════════════════
# NationalRestaurantSyncer
# ══════════════════════════════════════════════════════════════

class NationalRestaurantSyncer:
    """
    공공데이터포털 행정안전부_식품_일반음식점 API 동기화.

    API: https://www.data.go.kr/data/15154916/openapi.do
    페이지네이션: pageNo + numOfRows (max 100)
    """

    BATCH_SIZE   = 100
    RETURN_TYPE  = "json"
    STATUS_OPEN  = "01"

    _log = logging.getLogger(__name__)

    def __init__(self):
        self.api_key = settings.NATIONAL_API_KEY
        self.api_url = settings.NATIONAL_API_URL

        if not self.api_key:
            raise ValueError("NATIONAL_API_KEY 환경변수가 설정되지 않았습니다")
        if not self.api_url:
            raise ValueError("NATIONAL_API_URL이 settings.py에 설정되지 않았습니다")

    def fetch(self, page_no: int) -> list:
        """page_no 페이지 데이터를 가져온다. 실패 시 빈 리스트 반환."""
        params = {
            "serviceKey"         : self.api_key,
            "pageNo"             : page_no,
            "numOfRows"          : self.BATCH_SIZE,
            "returnType"         : self.RETURN_TYPE,
            "cond[SALS_STTS_CD::EQ]": self.STATUS_OPEN,
        }
        self._log.info("[NationalAPI] 페이지 %d 호출", page_no)

        for attempt in range(1, 4):
            try:
                resp = requests.get(self.api_url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.exceptions.Timeout:
                self._log.warning("[NationalAPI] 타임아웃 (시도 %d/3)", attempt)
                if attempt == 3:
                    return []
            except requests.exceptions.RequestException as exc:
                self._log.warning("[NationalAPI] 요청 실패 (시도 %d/3): %s", attempt, exc)
                if attempt == 3:
                    return []
            except ValueError:
                self._log.error("[NationalAPI] JSON 파싱 실패")
                return []

        if "response" not in data:
            self._log.warning("[NationalAPI] 'response' 키 없음")
            return []

        header = data["response"].get("header", {})
        code   = str(header.get("resultCode", ""))
        if code not in ("0", "00"):
            self._log.warning("[NationalAPI] 응답 코드: %s (%s)", code, header.get("resultMsg"))
            return []

        items_obj = data["response"].get("body", {}).get("items", {})
        if isinstance(items_obj, dict):
            items = items_obj.get("item", [])
        else:
            items = items_obj if isinstance(items_obj, list) else []

        self._log.info("[NationalAPI] %d건 수신", len(items))
        return items

    def save(self, rows: list) -> "tuple[int, int]":
        """rows를 DB에 upsert. 반환: (created, updated)"""
        created = updated = skipped = 0

        for row in rows:
            mgt_no = row.get("MNG_NO", "").strip()
            name   = row.get("BPLC_NM", "").strip()
            if not mgt_no or not name:
                skipped += 1
                continue

            if row.get("SALS_STTS_CD", "").strip() != self.STATUS_OPEN:
                skipped += 1
                continue

            biz_type = row.get("BZSTAT_SE_NM", "").strip()
            if "편의점" in name or "편의점" in biz_type:
                skipped += 1
                continue

            try:
                _, is_new = PublicRestaurantData.objects.update_or_create(
                    management_no=mgt_no,
                    defaults=self._build_defaults(row),
                )
                created += is_new
                updated += not is_new
            except Exception as exc:
                self._log.error("[NationalAPI] DB 저장 실패 MNG_NO=%s: %s", mgt_no, exc)
                skipped += 1

        self._log.info("[NationalAPI] 신규:%d / 갱신:%d / 스킵:%d", created, updated, skipped)
        return created, updated

    # ── 내부 헬퍼 ─────────────────────────────────────────────

    def _build_defaults(self, row: dict) -> dict:
        road  = row.get("ROAD_NM_ADDR", "").strip()
        jibun = row.get("LOTNO_ADDR",   "").strip()
        addr  = road or jibun

        province = self._extract_province(row.get("OPN_ATMY_GRP_CD", ""), addr)
        lat, lng = convert_tm_to_wgs84(row.get("CRD_INFO_X"), row.get("CRD_INFO_Y"))

        return {
            "name"                   : row.get("BPLC_NM", "").strip(),
            "address_road"           : road,
            "address_jibun"          : jibun,
            "province"               : province,
            "phone"                  : row.get("TELNO", "").strip(),
            "business_type"          : row.get("BZSTAT_SE_NM", "").strip(),
            "category_name"          : "",
            "sanitation_business_type": row.get("SNTTN_BZSTAT_NM", "").strip(),
            "license_date"           : self._parse_date_iso(row.get("LCPMT_YMD")),
            "status_code"            : row.get("SALS_STTS_CD", "").strip(),
            "area"                   : self._parse_float(row.get("FCLT_TOTAL_SCL")),
            "last_modified_at"       : self._parse_datetime_iso(row.get("DAT_UPDT_PNT")),
            "latitude"               : lat,
            "longitude"              : lng,
        }

    @staticmethod
    def _extract_province(opn_code: str, addr: str) -> str:
        opn_code = opn_code.strip()
        if opn_code and len(opn_code) >= 2:
            province = PROVINCE_CODE_MAP.get(opn_code[:2], "")
            if province:
                return province
        return addr.split()[0] if addr else ""

    @staticmethod
    def _parse_date_iso(val) -> "datetime.date | None":
        if not val or not val.strip():
            return None
        try:
            return datetime.strptime(val.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime_iso(val) -> "datetime | None":
        if not val or not val.strip():
            return None
        try:
            return datetime.strptime(val.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    @staticmethod
    def _parse_float(val) -> "float | None":
        if not val or not val.strip():
            return None
        try:
            return float(val.strip())
        except ValueError:
            return None


# ══════════════════════════════════════════════════════════════
# HygieneGradeSyncer
# ══════════════════════════════════════════════════════════════

class HygieneGradeSyncer:
    """
    식품안전나라 C004 위생등급 지정 현황 API 연동.
    업소명 + 시/도 기준으로 매칭 후 hygiene_grade 필드를 업데이트한다.

    API: http://openapi.foodsafetykorea.go.kr/api/{KEY}/C004/json/{start}/{end}
    """

    API_BASE   = "http://openapi.foodsafetykorea.go.kr/api"
    SERVICE_ID = "C004"
    BATCH_SIZE = 1000

    _log = logging.getLogger(__name__)

    def fetch(self, start: int = 1, end: int = 1000) -> "tuple[list, int]":
        url = f"{self.API_BASE}/{settings.FOOD_SAFETY_API_KEY}/{self.SERVICE_ID}/json/{start}/{end}"
        self._log.info("[HygieneAPI] 호출 %d~%d", start, end)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            self._log.error("[HygieneAPI] 요청 실패: %s", exc)
            return [], 0
        except ValueError:
            self._log.error("[HygieneAPI] JSON 파싱 실패")
            return [], 0

        service_data = data.get(self.SERVICE_ID, {})
        total = int(service_data.get("total_count", 0))
        rows  = service_data.get("row", [])
        self._log.info("[HygieneAPI] %d건 수신 (전체 %d건)", len(rows), total)
        return rows, total

    def save(self, rows: list) -> "tuple[int, int]":
        updated = skipped = 0

        for row in rows:
            if row.get("ASGN_CANCEL_YMD", "").strip():
                skipped += 1
                continue
            if row.get("CLSBIZ_DVS_CD_NM", "").strip() != "정상":
                skipped += 1
                continue

            name = row.get("BSSH_NM", "").strip()
            addr = row.get("ADDR",    "").strip()
            if not name or not addr:
                skipped += 1
                continue

            province = addr.split()[0]
            candidates = PublicRestaurantData.objects.filter(
                name=name,
                status_code=PublicRestaurantData.STATUS_OPEN,
            )
            if province:
                candidates = candidates.filter(
                    Q(address_road__startswith=province) |
                    Q(address_jibun__startswith=province)
                )

            cnt = candidates.update(
                hygiene_grade     =row.get("HG_ASGN_LV", "").strip(),
                hygiene_grade_no  =row.get("HG_ASGN_NO", "").strip(),
                hygiene_grade_from=parse_date(row.get("ASGN_FROM")),
                hygiene_grade_to  =parse_date(row.get("ASGN_TO")),
            )
            if cnt:
                updated += cnt
            else:
                skipped += 1

        self._log.info("[HygieneAPI] 완료 — 업데이트:%d / 스킵:%d", updated, skipped)
        return updated, skipped


# ══════════════════════════════════════════════════════════════
# ExcellentRestaurantSyncer
# ══════════════════════════════════════════════════════════════

class ExcellentRestaurantSyncer:
    """
    행정안전부 모범음식점정보 API 연동.
    management_no(관리번호) 기준 정확 매칭.

    API: https://apis.data.go.kr/1741000/excellent_restaurant_info/info
    """

    BATCH_SIZE = 100
    _log = logging.getLogger(__name__)

    def fetch(self, page_no: int = 1, num_of_rows: int = 1000) -> "tuple[list, int]":
        self._log.info("[ExcellentAPI] 페이지 %d 호출", page_no)
        try:
            resp = requests.get(settings.EXCELLENT_RESTAURANT_URL, params={
                "serviceKey": settings.NATIONAL_API_KEY,
                "pageNo"    : page_no,
                "numOfRows" : num_of_rows,
                "type"      : "json",
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            self._log.error("[ExcellentAPI] 요청 실패: %s", exc)
            return [], 0
        except ValueError:
            self._log.error("[ExcellentAPI] JSON 파싱 실패")
            return [], 0

        body  = data.get("response", {}).get("body", {})
        total = int(body.get("totalCount", 0))
        items = body.get("items", {})
        rows  = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(rows, dict):
            rows = [rows]

        self._log.info("[ExcellentAPI] %d건 수신 (전체 %d건)", len(rows), total)
        return rows, total

    def save(self, rows: list) -> "tuple[int, int]":
        updated = skipped = 0

        for row in rows:
            mng_no = row.get("MNG_NO", "").strip()
            if not mng_no:
                skipped += 1
                continue
            if row.get("DSGN_RTRCN_YMD", "").strip():
                skipped += 1
                continue
            if row.get("SALS_STTS_CD", "").strip() != "01":
                skipped += 1
                continue

            cnt = PublicRestaurantData.objects.filter(management_no=mng_no).update(
                is_excellent_restaurant=True,
                excellent_dsgn_ymd    =parse_date(row.get("DSGN_YMD")),
                excellent_re_dsgn_ymd =parse_date(row.get("RE_DSGN_YMD")),
                excellent_food_type   =row.get("FD_OF_TYPE",   "").strip(),
                excellent_main_menu   =row.get("PRINC_FD_KND", "").strip(),
            )
            updated += cnt
            if not cnt:
                skipped += 1

        self._log.info("[ExcellentAPI] 완료 — 업데이트:%d / 스킵:%d", updated, skipped)
        return updated, skipped


# ══════════════════════════════════════════════════════════════
# AnsimRestaurantSyncer
# ══════════════════════════════════════════════════════════════

class AnsimRestaurantSyncer:
    """
    농림축산식품부 안심식당 API 연동.
    RELAX_SEQ 매칭 우선, 없으면 이름+주소 앞 20자 fallback.

    API: http://211.237.50.150:7080/openapi/{key}/xml/Grid_20200713000000000605_1/{start}/{end}
    """

    BATCH_SIZE = 1000
    _BASE_URL  = ("http://211.237.50.150:7080/openapi"
                  "/{key}/xml/Grid_20200713000000000605_1/{start}/{end}")
    _log       = logging.getLogger(__name__)

    def _build_url(self, start: int, end: int) -> str:
        key = settings.ANSIM_RESTAURANT_API_KEY or "sample"
        return self._BASE_URL.format(key=key, start=start, end=end)

    def fetch(self, start_row: int = 1) -> "tuple[list, int]":
        end_row = start_row + self.BATCH_SIZE - 1
        self._log.info("[AnsimAPI] 행 %d~%d 호출", start_row, end_row)
        try:
            resp = requests.get(self._build_url(start_row, end_row), timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            self._log.error("[AnsimAPI] 요청 실패: %s", exc)
            return [], 0

        try:
            root     = ET.fromstring(resp.content)
            total_el = root.find("totalCnt")
            total    = int(total_el.text) if total_el is not None else 0
            rows     = [
                {child.tag: (child.text or "").strip() for child in row}
                for row in root.findall("row")
            ]
        except Exception as exc:
            self._log.error("[AnsimAPI] XML 파싱 실패: %s", exc)
            return [], 0

        self._log.info("[AnsimAPI] %d건 수신 (전체 %d건)", len(rows), total)
        return rows, total

    def save(self, rows: list) -> "tuple[int, int]":
        updated = skipped = 0

        for row in rows:
            if row.get("RELAX_USE_YN") != "Y":
                skipped += 1
                continue

            seq  = row.get("RELAX_SEQ", "").strip()
            name = row.get("RELAX_RSTRNT_NM", "").strip()
            addr = row.get("RELAX_ADD1", "").strip()
            reg  = parse_date(row.get("RELAX_RSTRNT_REG_DT"))

            if not name:
                skipped += 1
                continue

            # 1차: RELAX_SEQ 직접 매칭
            if seq:
                cnt = PublicRestaurantData.objects.filter(ansim_seq=seq).update(
                    is_ansim_restaurant=True,
                    ansim_reg_dt=reg,
                )
                if cnt:
                    updated += cnt
                    continue

            # 2차: 이름 + 주소 앞 20자 매칭 (1:1 결과만)
            qs = PublicRestaurantData.objects.filter(name=name)
            if addr:
                qs = qs.filter(address_prefix_q(addr))
            if qs.count() == 1:
                qs.update(is_ansim_restaurant=True, ansim_reg_dt=reg, ansim_seq=seq)
                updated += 1
            else:
                skipped += 1

        return updated, skipped


# ══════════════════════════════════════════════════════════════
# GoodPriceShopSyncer
# ══════════════════════════════════════════════════════════════

class GoodPriceShopSyncer:
    """
    행정안전부 착한가격업소 현황 API 연동.
    업소명 + 주소 앞 20자 매칭, 1:1 결과일 때만 업데이트.

    API: https://api.odcloud.kr/api/3045247/v1/uddi:12a36b40-6230-4401-b647-b8456a789c7f
    """

    BATCH_SIZE = 1000
    _URL       = ("https://api.odcloud.kr/api/3045247/v1"
                  "/uddi:12a36b40-6230-4401-b647-b8456a789c7f")
    _log       = logging.getLogger(__name__)

    def fetch(self, page: int = 1) -> "tuple[list, int]":
        self._log.info("[GoodPriceAPI] 페이지 %d 호출", page)
        try:
            resp = requests.get(self._URL, params={
                "serviceKey": settings.NATIONAL_API_KEY,
                "page"      : page,
                "perPage"   : self.BATCH_SIZE,
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            self._log.error("[GoodPriceAPI] 요청 실패: %s", exc)
            return [], 0
        except ValueError:
            self._log.error("[GoodPriceAPI] JSON 파싱 실패")
            return [], 0

        total = data.get("totalCount", 0)
        rows  = data.get("data", [])
        self._log.info("[GoodPriceAPI] %d건 수신 (전체 %d건)", len(rows), total)
        return rows, total

    def save(self, rows: list) -> "tuple[int, int]":
        updated = skipped = 0

        for row in rows:
            name = (row.get("업소명") or "").strip()
            addr = (row.get("주소")   or "").strip()
            if not name:
                skipped += 1
                continue

            menu_str = self._build_menu_str(row)

            qs = PublicRestaurantData.objects.filter(name=name)
            if addr:
                qs = qs.filter(address_prefix_q(addr))

            if qs.count() == 1:
                qs.update(is_goodprice_shop=True, goodprice_menu=menu_str[:300])
                updated += 1
            else:
                skipped += 1

        return updated, skipped

    @staticmethod
    def _build_menu_str(row: dict) -> str:
        parts = []
        for i in range(1, 5):
            m = (row.get(f"메뉴{i}") or "").strip()
            p = (row.get(f"가격{i}") or "").strip()
            if m and p:
                parts.append(f"{m} {int(p):,}원" if p.isdigit() else f"{m} {p}원")
            elif m:
                parts.append(m)
        return " / ".join(parts)
