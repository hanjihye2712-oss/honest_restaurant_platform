"""
python manage.py seed_sales           # 기본: 2025-01-01 ~ 2026-05-15
python manage.py seed_sales --clear   # 기존 데이터 삭제 후 재생성
"""
import random
from datetime import date, timedelta, datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from sales.models import ManagedRestaurant, SaleRecord, SaleItem


# ── 기본 메뉴 데이터 ─────────────────────────────────────────
MEALS = [
    ("순대국",          7000),
    ("살코기 순대국",   7000),
    ("순대만 순대국",   7000),
    ("부대찌개",        7000),
    ("술국",            15000),
    ("순대곱창전골 중", 20000),
    ("순대곱창전골 대", 30000),
    ("순대곱창볶음 중", 20000),
    ("순대곱창볶음 대", 30000),
]
LIQUORS = [("소주", 3000), ("맥주", 3000)]
DRINKS  = [("콜라", 1000), ("사이다", 1000)]

# ── 메뉴별 기본 가중치 (높을수록 자주 선택) ──────────────────
BASE_WEIGHTS = {
    "순대국":          40,   # 대표 메뉴 — 항상 높음
    "살코기 순대국":   25,
    "순대만 순대국":   20,
    "부대찌개":        18,
    "순대곱창전골 중": 12,
    "순대곱창전골 대": 8,
    "순대곱창볶음 중": 10,
    "순대곱창볶음 대": 6,
    "술국":            5,    # 낮게 유지
}

# ── 계절별 보정 계수 (month → {메뉴: 배율}) ──────────────────
SEASON_BOOST = {
    # 봄 (3~5월): 순대국 강세
    3:  {"순대국": 1.3, "부대찌개": 1.1, "술국": 0.8},
    4:  {"순대국": 1.3, "살코기 순대국": 1.2},
    5:  {"순대국": 1.2, "순대만 순대국": 1.1},
    # 여름 (6~8월): 전골류 감소, 볶음 소폭 증가
    6:  {"순대곱창전골 중": 0.7, "순대곱창전골 대": 0.6, "순대곱창볶음 중": 1.2},
    7:  {"순대곱창전골 중": 0.6, "순대곱창전골 대": 0.5, "술국": 0.5},
    8:  {"순대곱창전골 중": 0.6, "순대국": 0.9, "순대곱창볶음 대": 1.1},
    # 가을 (9~11월): 전골류 회복
    9:  {"순대곱창전골 중": 1.2, "순대곱창전골 대": 1.1},
    10: {"순대곱창전골 중": 1.4, "순대곱창전골 대": 1.2, "술국": 1.1},
    11: {"순대곱창전골 대": 1.3, "순대곱창볶음 대": 1.2, "순대국": 1.1},
    # 겨울 (12~2월): 순대국 최강, 전골 성수기
    12: {"순대국": 1.5, "순대곱창전골 중": 1.5, "순대곱창전골 대": 1.4, "부대찌개": 1.3},
    1:  {"순대국": 1.6, "순대곱창전골 중": 1.4, "순대곱창전골 대": 1.3, "술국": 1.2},
    2:  {"순대국": 1.4, "살코기 순대국": 1.2, "순대곱창전골 중": 1.3},
}


def get_meal_weights(month: int) -> list:
    """계절 보정이 적용된 메뉴 가중치 리스트 반환"""
    boosts = SEASON_BOOST.get(month, {})
    weights = []
    for name, _ in MEALS:
        w = BASE_WEIGHTS.get(name, 10)
        w = int(w * boosts.get(name, 1.0))
        weights.append(max(w, 1))
    return weights


def build_order(month: int, is_weekend: bool, is_evening: bool) -> list:
    """랜덤 주문 1건 → [(menu_name, qty, price), ...]"""
    items   = []
    weights = get_meal_weights(month)
    names   = [m[0] for m in MEALS]
    prices  = {m[0]: m[1] for m in MEALS}

    # 저녁/주말엔 테이블당 메뉴 수 증가
    if is_evening and is_weekend:
        meal_count = random.choices([1, 2, 3], weights=[20, 50, 30])[0]
    elif is_evening:
        meal_count = random.choices([1, 2], weights=[40, 60])[0]
    else:
        meal_count = random.choices([1, 2], weights=[70, 30])[0]

    chosen = set()
    for _ in range(meal_count):
        pick = random.choices(names, weights=weights)[0]
        if pick not in chosen:
            chosen.add(pick)
            qty = random.randint(1, 3) if is_evening else random.randint(1, 2)
            items.append((pick, qty, prices[pick]))

    # 주류
    if is_evening:
        liq_prob = 0.75 if is_weekend else 0.55
        if random.random() < liq_prob:
            liq_count = random.choices([1, 2], weights=[40, 60])[0]
            for liq in random.sample(LIQUORS, min(liq_count, len(LIQUORS))):
                qty = random.randint(2, 6) if is_weekend else random.randint(1, 4)
                items.append((liq[0], qty, liq[1]))

    # 음료
    drink_prob = 0.4 if is_evening else 0.25
    if random.random() < drink_prob:
        drink = random.choice(DRINKS)
        items.append((drink[0], random.randint(1, 3), drink[1]))

    return items


class Command(BaseCommand):
    help = "정직순대국 매출 시드 데이터 생성 (2025-01-01 ~ 2026-05-15)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="기존 데이터 전체 삭제 후 재생성")

    def handle(self, *args, **options):
        # 정직순대국 관리 매장 가져오기 또는 생성
        from datetime import date as _date
        restaurant, created = ManagedRestaurant.objects.get_or_create(
            name='정직순대국',
            defaults={
                'owner_name': '김정직',
                'business_type': '한식',
                'status': 'active',
                'joined_at': _date(2025, 1, 1),
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("  관리 매장 '정직순대국' 자동 등록"))

        if options["clear"]:
            deleted, _ = SaleRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  기존 데이터 {deleted}건 삭제"))

        start   = date(2025, 1, 1)
        end     = date(2026, 5, 15)
        current = start
        total_records = 0

        self.stdout.write(self.style.MIGRATE_HEADING("▶ 매출 시드 데이터 생성 시작"))

        while current <= end:
            is_weekend = current.weekday() >= 5
            month      = current.month

            # 주말 > 평일, 월별 성수기 반영
            season_factor = {12: 1.4, 1: 1.3, 2: 1.2, 10: 1.2, 11: 1.1}.get(month, 1.0)
            if is_weekend:
                daily_count = int(random.randint(22, 38) * season_factor)
            else:
                daily_count = int(random.randint(10, 18) * season_factor)

            records_batch = []
            items_map     = {}   # order_id → (items, ts)

            for _ in range(daily_count):
                hour       = random.randint(11, 21)
                is_evening = hour >= 17
                ts = timezone.make_aware(
                    datetime(current.year, current.month, current.day,
                             hour, random.randint(0, 59))
                )
                order_items = build_order(month, is_weekend, is_evening)
                if not order_items:
                    continue
                amount   = sum(qty * price for _, qty, price in order_items)
                order_id = (f"SEED_{current.strftime('%Y%m%d')}"
                            f"_{random.randint(10000, 99999)}")

                records_batch.append(
                    SaleRecord(order_id=order_id, amount=amount, status="DONE", restaurant=restaurant)
                )
                items_map[order_id] = (order_items, ts)

            SaleRecord.objects.bulk_create(records_batch, ignore_conflicts=True)

            for order_id, (order_items, ts) in items_map.items():
                try:
                    record = SaleRecord.objects.get(order_id=order_id)
                    SaleRecord.objects.filter(pk=record.pk).update(created_at=ts)
                    SaleItem.objects.bulk_create([
                        SaleItem(sale_record=record,
                                 menu_name=n, quantity=q, price=p)
                        for n, q, p in order_items
                    ])
                    total_records += 1
                except SaleRecord.DoesNotExist:
                    pass

            current += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f"✅ 완료: {total_records:,}건 주문 생성"))
