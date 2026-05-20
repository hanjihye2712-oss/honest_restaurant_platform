"""
착한가격업소 동기화 management command

사용법:
    python manage.py sync_goodprice_shops

API: 행정안전부 착한가격업소 현황 (api.odcloud.kr)
키: NATIONAL_API_KEY (.env)
"""
from django.core.management.base import BaseCommand

from honest_restaurant.services import GoodPriceShopSyncer


class Command(BaseCommand):
    help = "행정안전부 착한가격업소 데이터를 가져와 DB를 업데이트합니다."

    def handle(self, *args, **options):
        syncer    = GoodPriceShopSyncer()
        MAX_RETRY = 3
        batch     = GoodPriceShopSyncer.BATCH_SIZE

        _, total = syncer.fetch(page=1)
        if not total:
            self.stderr.write("API 조회 실패 또는 데이터 없음")
            return

        self.stdout.write(f"전체 {total:,}건 동기화 시작")

        total_updated = total_skipped = processed = 0
        page = 1

        while processed < total:
            rows = []
            for attempt in range(1, MAX_RETRY + 1):
                rows, _ = syncer.fetch(page=page)
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

            if len(rows) < batch:
                break
            page += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료 — 총 업데이트:{total_updated:,} / 스킵:{total_skipped:,}"
                f" / 처리:{processed:,}건"
            )
        )
