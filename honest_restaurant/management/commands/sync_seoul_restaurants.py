from django.core.management.base import BaseCommand

from honest_restaurant.services import BATCH_SIZE, fetch_restaurants, save_restaurants

class Command(BaseCommand):
    """
    서울시 일반음식점 인허가 데이터 전체 동기화

    사용법:
        python manage.py sync_seoul_restaurants           # 전체 동기화
        python manage.py sync_seoul_restaurants --start 1 --end 5000  # 범위 지정
    """

    help = "서울 열린데이터광장 LOCALDATA_072404 전체 동기화"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start",
            type=int,
            default=1,
            help="시작 인덱스 (기본값: 1)",
        )
        parser.add_argument(
            "--end",
            type=int,
            default=None,
            help="종료 인덱스 (기본값: 끝까지)",
        )

    def handle(self, *args, **options):
        start      = options["start"]
        end_limit  = options["end"]          # None이면 마지막까지
        total_created = 0
        total_updated = 0
        page = 0

        self.stdout.write(self.style.MIGRATE_HEADING("▶ 서울시 식당 데이터 동기화 시작"))

        while True:
            batch_start = start + page * BATCH_SIZE
            batch_end   = batch_start + BATCH_SIZE - 1

            # --end 옵션으로 범위 제한
            if end_limit and batch_start > end_limit:
                break

            rows = fetch_restaurants(batch_start, batch_end)

            if not rows:
                # 데이터 소진 or 에러 → 종료
                break

            created, updated = save_restaurants(rows)
            total_created += created
            total_updated += updated

            self.stdout.write(
                f"  페이지 {page + 1:>4} | {batch_start:>7}~{batch_end:<7} "
                f"| 신규 {created:>5}건 / 갱신 {updated:>5}건"
            )

            # 마지막 배치 (1000건 미만이면 마지막 페이지)
            if len(rows) < BATCH_SIZE:
                break

            page += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ 동기화 완료 — 총 신규: {total_created}건 / 총 갱신: {total_updated}건"
            )
        )