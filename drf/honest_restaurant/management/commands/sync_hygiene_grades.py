"""
위생등급 동기화 management command

사용법:
    python manage.py sync_hygiene_grades           # 전체 동기화
    python manage.py sync_hygiene_grades --start 1 --end 500
"""
from django.core.management.base import BaseCommand

from honest_restaurant.services import HygieneGradeSyncer


class Command(BaseCommand):
    help = "식품안전나라 C004 위생등급 데이터를 가져와 DB를 업데이트합니다."

    def add_arguments(self, parser):
        parser.add_argument("--start", type=int, default=1,    help="시작 인덱스 (기본값: 1)")
        parser.add_argument("--end",   type=int, default=None, help="종료 인덱스 (기본값: 전체)")

    def handle(self, *args, **options):
        syncer = HygieneGradeSyncer()
        start  = options["start"]
        end    = options["end"]

        # end가 지정되지 않으면 전체 수를 먼저 조회
        if not end:
            _, total = syncer.fetch(1, 1)
            if not total:
                self.stderr.write("API 조회 실패 또는 데이터 없음")
                return
            end = total
            self.stdout.write(f"전체 {total:,}건 동기화 시작")

        total_updated = total_skipped = 0
        batch   = HygieneGradeSyncer.BATCH_SIZE
        MAX_RETRY = 3

        for s in range(start, end + 1, batch):
            e = min(s + batch - 1, end)

            rows = []
            for attempt in range(1, MAX_RETRY + 1):
                rows, _ = syncer.fetch(s, e)
                if rows:
                    break
                self.stdout.write(f"  [{s}~{e}] 타임아웃 재시도 {attempt}/{MAX_RETRY}")

            if not rows:
                self.stdout.write(f"  [{s}~{e}] 3회 실패 — 건너뜀")
                continue

            updated, skipped = syncer.save(rows)
            total_updated += updated
            total_skipped += skipped
            self.stdout.write(f"  [{s}~{e}] 업데이트:{updated} / 스킵:{skipped}")

        self.stdout.write(
            self.style.SUCCESS(
                f"완료 — 총 업데이트:{total_updated:,} / 스킵:{total_skipped:,}"
            )
        )
