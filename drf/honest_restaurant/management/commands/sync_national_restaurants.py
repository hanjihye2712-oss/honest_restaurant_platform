from django.core.management.base import BaseCommand

from honest_restaurant.services import NationalRestaurantSyncer


class Command(BaseCommand):
    """
    공공데이터포털 행정안전부_식품_일반음식점 API 데이터 동기화

    API: https://www.data.go.kr/data/15154916/openapi.do
    - pageNo + numOfRows 페이지네이션 (max: 100)
    - 영업 중인 가게만 저장 (SALS_STTS_CD='01')

    사용법:
        python manage.py sync_national_restaurants                    # 전체 동기화
        python manage.py sync_national_restaurants --max-pages 10     # 처음 10페이지만
        python manage.py sync_national_restaurants --clear            # 기존 데이터 삭제 후 동기화
    """

    help = "공공데이터포털 전국 음식점 데이터 동기화"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-pages",
            type=int,
            default=None,
            help="동기화할 최대 페이지 수 (기본값: 무제한)",
        )
        parser.add_argument(
            "--start-page",
            type=int,
            default=1,
            help="시작 페이지 번호 (기본값: 1, 중단된 경우 이어받기 용도)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="기존 데이터를 삭제한 후 동기화 (처음 1회만 권장)",
        )

    def handle(self, *args, **options):
        from honest_restaurant.models import PublicRestaurantData

        max_pages = options["max_pages"]
        clear_data = options["clear"]

        # ── 기존 데이터 삭제 ──────────────────────────────
        if clear_data:
            confirm = input(
                "⚠️  기존 모든 식당 데이터를 삭제하겠습니다. 계속하시겠습니까? (yes/no): "
            )
            if confirm.lower() != "yes":
                self.stdout.write(self.style.WARNING("작업 취소됨"))
                return

            count, _ = PublicRestaurantData.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"✅ 기존 데이터 {count:,}건 삭제 완료\n")
            )

        # ── API 동기화 ──────────────────────────────────
        total_created = 0
        total_updated = 0
        page_no = options["start_page"]

        try:
            syncer = NationalRestaurantSyncer()
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"❌ 초기화 오류: {e}"))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "▶ 공공데이터포털 전국 음식점 데이터 동기화 시작\n"
            )
        )

        while True:
            # 최대 페이지 도달 확인
            if max_pages and page_no > max_pages:
                self.stdout.write(
                    self.style.WARNING(f"📍 최대 페이지({max_pages}) 도달\n")
                )
                break

            # 데이터 조회
            rows = syncer.fetch(page_no)
            if not rows:
                self.stdout.write(self.style.WARNING("📍 더 이상 데이터 없음\n"))
                break

            # 데이터 저장
            created, updated = syncer.save(rows)
            total_created += created
            total_updated += updated

            # 진행 상황 출력
            row_count = len(rows)
            self.stdout.write(
                f"  페이지 {page_no:>4} | {row_count:>3}건 수신 | "
                f"신규 {created:>5}건 / 갱신 {updated:>5}건"
            )

            # 마지막 페이지 확인 (수신한 행 수 < BATCH_SIZE)
            if row_count < syncer.BATCH_SIZE:
                self.stdout.write(self.style.WARNING("📍 마지막 페이지 도달\n"))
                break

            page_no += 1

        # ── 결과 요약 ──────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ 동기화 완료\n"
                f"   총 신규: {total_created:,}건\n"
                f"   총 갱신: {total_updated:,}건\n"
                f"   처리 페이지: {page_no - 1}페이지"
            )
        )
