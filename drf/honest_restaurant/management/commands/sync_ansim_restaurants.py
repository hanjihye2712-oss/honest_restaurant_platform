"""
안심식당 동기화 management command

사용법:
    python manage.py sync_ansim_restaurants

API 키: .env → ANSIM_RESTAURANT_API_KEY
등록: http://211.237.50.150:7080
"""
from django.core.management.base import BaseCommand

from honest_restaurant.services import AnsimRestaurantSyncer


class Command(BaseCommand):
    help = "농림축산식품부 안심식당 데이터를 가져와 DB를 업데이트합니다."

    def handle(self, *args, **options):
        syncer    = AnsimRestaurantSyncer()
        MAX_RETRY = 3
        batch     = AnsimRestaurantSyncer.BATCH_SIZE

        # 전체 건수 먼저 파악
        _, total = syncer.fetch(start_row=1)
        if not total:
            self.stderr.write("API 조회 실패 또는 데이터 없음 — API 키를 확인하세요.")
            return

        self.stdout.write(f"전체 {total:,}건 동기화 시작 (USE_YN=Y 만 저장)")

        total_updated = total_skipped = processed = 0
        start_row = 1

        while processed < total:
            rows = []
            for attempt in range(1, MAX_RETRY + 1):
                rows, _ = syncer.fetch(start_row=start_row)
                if rows:
                    break
                self.stdout.write(f"  [행 {start_row}~] 타임아웃 재시도 {attempt}/{MAX_RETRY}")

            if not rows:
                self.stdout.write(f"  [행 {start_row}~] 3회 실패 — 종료")
                break

            updated, skipped = syncer.save(rows)
            total_updated += updated
            total_skipped += skipped
            processed     += len(rows)
            self.stdout.write(
                f"  [행 {start_row}~{start_row + len(rows) - 1}]"
                f" 업데이트:{updated} / 스킵:{skipped}"
                f" ({processed:,}/{total:,})"
            )

            if len(rows) < batch:
                break
            start_row += batch

        self.stdout.write(
            self.style.SUCCESS(
                f"완료 — 총 업데이트:{total_updated:,} / 스킵:{total_skipped:,}"
                f" / 처리:{processed:,}건"
            )
        )
