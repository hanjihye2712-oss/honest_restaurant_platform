"""
모범음식점 동기화 management command

사용법:
    python manage.py sync_excellent_restaurants
"""
from django.core.management.base import BaseCommand

from honest_restaurant.services import ExcellentRestaurantSyncer


class Command(BaseCommand):
    help = "행정안전부 모범음식점 데이터를 가져와 DB를 업데이트합니다."

    def handle(self, *args, **options):
        syncer    = ExcellentRestaurantSyncer()
        MAX_RETRY = 3
        batch     = ExcellentRestaurantSyncer.BATCH_SIZE

        # 전체 건수 먼저 파악
        _, total = syncer.fetch(page_no=1, num_of_rows=1)
        if not total:
            self.stderr.write("API 조회 실패 또는 데이터 없음")
            return

        self.stdout.write(f"전체 {total:,}건 동기화 시작")

        total_updated = total_skipped = processed = 0
        page = 1

        while processed < total:
            rows = []
            for attempt in range(1, MAX_RETRY + 1):
                rows, _ = syncer.fetch(page_no=page, num_of_rows=batch)
                if rows:
                    break
                self.stdout.write(f"  [페이지 {page}] 타임아웃 재시도 {attempt}/{MAX_RETRY}")

            if not rows:
                self.stdout.write(f"  [페이지 {page}] 3회 실패 — 종료")
                break

            updated, skipped = syncer.save(rows)
            total_updated += updated
            total_skipped += skipped
            processed     += len(rows)
            self.stdout.write(
                f"  [페이지 {page}] 업데이트:{updated} / 스킵:{skipped}"
                f" ({processed:,}/{total:,})"
            )

            # 실제 반환 건수가 요청보다 적으면 마지막 페이지
            if len(rows) < batch:
                break
            page += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료 — 총 업데이트:{total_updated:,} / 스킵:{total_skipped:,}"
                f" / 처리:{processed:,}건"
            )
        )
