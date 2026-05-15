"""
좌표(latitude/longitude)가 없는 식당을 카카오 주소 검색 API로 보완.

사용법:
    python manage.py geocode_missing_coords              # 전체 처리
    python manage.py geocode_missing_coords --limit 100  # 최대 100건
    python manage.py geocode_missing_coords --dry-run    # 실제 저장 없이 결과만 출력

필요 환경변수:
    KAKAO_REST_API_KEY  (카카오 개발자 콘솔 → 내 애플리케이션 → 앱 키 → REST API 키)
"""

import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pyproj import Transformer

from honest_restaurant.models import PublicRestaurantData

_WGS84_TO_TM = Transformer.from_crs("EPSG:4326", "EPSG:5174", always_xy=True)

KAKAO_GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"


def kakao_geocode(address: str, rest_key: str) -> tuple[float, float] | None:
    """주소 → (lng_wgs84, lat_wgs84) 반환. 실패 시 None."""
    try:
        resp = requests.get(
            KAKAO_GEOCODE_URL,
            params={"query": address, "analyze_type": "similar"},
            headers={"Authorization": f"KakaoAK {rest_key}"},
            timeout=5,
        )
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if not docs:
            return None
        doc = docs[0]
        return float(doc["x"]), float(doc["y"])  # (lng, lat) WGS84
    except Exception:
        return None


class Command(BaseCommand):
    help = "좌표 없는 식당을 카카오 주소 API로 geocode 후 EPSG:5174로 저장"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0,
                            help="처리할 최대 건수 (0=전체)")
        parser.add_argument("--dry-run", action="store_true",
                            help="DB 저장 없이 결과만 출력")
        parser.add_argument("--delay", type=float, default=0.1,
                            help="요청 간 지연(초), 기본 0.1")

    def handle(self, *args, **options):
        rest_key = settings.KAKAO_REST_API_KEY
        if not rest_key:
            raise CommandError(
                ".env 파일에 KAKAO_REST_API_KEY를 설정해주세요.\n"
                "카카오 개발자 콘솔 → 내 애플리케이션 → 앱 키 → REST API 키"
            )

        qs = (
            PublicRestaurantData.objects
            .filter(latitude__isnull=True)
            .exclude(address_road="")
        )
        total = qs.count()
        if options["limit"]:
            qs = qs[: options["limit"]]

        self.stdout.write(f"좌표 없는 식당: {total}개 (처리 대상: {qs.count()}개)")

        ok = fail = skip = 0
        for r in qs:
            address = r.address_road or r.address_jibun
            if not address:
                skip += 1
                continue

            result = kakao_geocode(address, rest_key)
            time.sleep(options["delay"])

            if result is None:
                fail += 1
                self.stdout.write(
                    self.style.WARNING(f"  [실패] pk={r.pk} {r.name} ({address})")
                )
                continue

            lng_wgs, lat_wgs = result
            # WGS84 → EPSG:5174 (모델의 latitude/longitude 단위)
            lng_tm, lat_tm = _WGS84_TO_TM.transform(lng_wgs, lat_wgs)

            if not options["dry_run"]:
                r.latitude  = lat_tm
                r.longitude = lng_tm
                r.save(update_fields=["latitude", "longitude"])

            ok += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [완료] pk={r.pk} {r.name} → lat={lat_tm:.1f} lng={lng_tm:.1f}"
                )
            )

        self.stdout.write(
            f"\n완료: {ok}개 저장, {fail}개 실패, {skip}개 주소없음"
            + (" (dry-run: 실제 저장 안됨)" if options["dry_run"] else "")
        )
