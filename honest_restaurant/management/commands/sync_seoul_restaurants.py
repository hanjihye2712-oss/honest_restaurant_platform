from django.core.management.base import BaseCommand

from honest_restaurant.views import SeoulRestaurantSyncer


class Command(BaseCommand):
    """
    서울시 음식점 인허가 데이터 전체 동기화

    사용법:
        python manage.py sync_seoul_restaurants                         # 일반음식점 전체
        python manage.py sync_seoul_restaurants --type 휴게음식점       # 휴게음식점 전체
        python manage.py sync_seoul_restaurants --start 1 --end 5000   # 범위 지정
    """

    help = "서울 열린데이터광장 음식점 인허가 데이터 동기화"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            dest="restaurant_type",
            choices=list(SeoulRestaurantSyncer.SERVICE_MAP.keys()),
            default="일반음식점",
            help="음식점 유형 (기본값: 일반음식점)",
        )
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
        restaurant_type = options["restaurant_type"]
        start           = options["start"]
        end_limit       = options["end"]
        total_created   = 0
        total_updated   = 0
        page            = 0

        syncer = SeoulRestaurantSyncer(restaurant_type)
        batch  = SeoulRestaurantSyncer.BATCH_SIZE

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"▶ 서울시 {restaurant_type} 데이터 동기화 시작")
        )

        while True:
            batch_start = start + page * batch
            batch_end   = batch_start + batch - 1

            if end_limit and batch_start > end_limit:
                break

            rows = syncer.fetch(batch_start, batch_end)
            if not rows:
                break

            created, updated = syncer.save(rows)
            total_created   += created
            total_updated   += updated

            self.stdout.write(
                f"  페이지 {page + 1:>4} | {batch_start:>7}~{batch_end:<7} "
                f"| 신규 {created:>5}건 / 갱신 {updated:>5}건"
            )

            if len(rows) < batch:
                break

            page += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ 동기화 완료 — 총 신규: {total_created}건 / 총 갱신: {total_updated}건"
            )
        )
