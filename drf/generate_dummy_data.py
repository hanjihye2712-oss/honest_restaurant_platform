"""
신목사골칼국수 (pk=866252) 대시보드 테스트용 더미 데이터 생성 스크립트
- 2025-01-01 ~ 2026-05-27 기간
- 리뷰 / 영수증인증 / 북마크 / AI프로필 / AI리포트 / 매출 / 마케팅 포스트
실행: python manage.py shell < generate_dummy_data.py
또는: python generate_dummy_data.py (manage.py와 같은 경로에서)
"""
import os, sys, django, random
from datetime import date, timedelta, datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction

from honest_restaurant.models import PublicRestaurantData, ReceiptVerification
from interactions.models import Bookmark, Review, Rating
from ai.ai_review_classifier.models import (
    RestaurantAIProfile, ReviewClassificationResult,
)
from ai.ai_report.models import RestaurantAIReport
from sales.models import ManagedRestaurant, SaleRecord, SaleItem
from marketing.models import MarketingPost

# ─────────────────────────────────────────
RESTAURANT_PK = 866252
OWNER_USERNAME = "hanjihye"
START_DATE     = date(2025, 1, 1)
END_DATE       = date(2026, 5, 27)
NUM_DUMMY_USERS = 120
random.seed(42)
# ─────────────────────────────────────────

rng = random.Random(42)

def rand_dt(start: date, end: date) -> datetime:
    """start~end 사이 무작위 naive datetime → aware로 반환."""
    delta = (end - start).days
    d = start + timedelta(days=rng.randint(0, delta))
    h = rng.randint(9, 21)
    m = rng.randint(0, 59)
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, m))


# ══════════════════════════════════════════
# 0. 기본 객체 로드
# ══════════════════════════════════════════
restaurant = PublicRestaurantData.objects.get(pk=RESTAURANT_PK)
owner       = User.objects.get(username=OWNER_USERNAME)
print(f"[대상] {restaurant.name} (pk={restaurant.pk})")


# ══════════════════════════════════════════
# 1. 더미 유저 생성 (dummy_u001 ~ dummy_u120)
# ══════════════════════════════════════════
print("[1] 더미 유저 생성 중...")
dummy_users = []
for i in range(1, NUM_DUMMY_USERS + 1):
    uname = f"dummy_u{i:03d}"
    u, _ = User.objects.get_or_create(
        username=uname,
        defaults={"email": f"{uname}@example.com", "password": "!"},
    )
    dummy_users.append(u)
print(f"    → {len(dummy_users)}명 준비 완료")


# ══════════════════════════════════════════
# 2. 영수증 인증 (ReceiptVerification)
#    - 100건 approved / 5건 pending / 3건 rejected
# ══════════════════════════════════════════
print("[2] 영수증 인증 생성 중...")
existing_rv_users = set(
    ReceiptVerification.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
rv_batch = []
comments = [
    "칼국수가 정말 진하고 맛있었어요!",
    "가격 대비 양이 많아요. 재방문 의사 있음.",
    "국물이 끝내줘요. 매일 와도 질리지 않을 것 같아요.",
    "사장님이 친절하십니다. 위생도 깔끔해요.",
    "수제비도 같이 시켜봤는데 두 가지 다 맛있었어요.",
    "점심 시간에 줄이 길어도 기다릴 만한 집이에요.",
    "사골 육수가 진짜 사골인 것 같아요. 묵직하고 고소해요.",
    "인증된 정직 식당, 가격도 메뉴판 그대로였어요!",
    "주차 공간이 조금 부족한 게 아쉽지만 음식은 최고.",
    "들깨칼국수 강추합니다. 고소함이 남달라요.",
]

statuses_plan = (
    [(ReceiptVerification.STATUS_APPROVED, END_DATE - timedelta(days=0))] * 100
    + [(ReceiptVerification.STATUS_PENDING, END_DATE)] * 5
    + [(ReceiptVerification.STATUS_REJECTED, END_DATE - timedelta(days=30))] * 3
)
rng.shuffle(statuses_plan)

rv_count = 0
for u, (status, before_date) in zip(dummy_users, statuses_plan):
    if u.id in existing_rv_users:
        continue
    dt = rand_dt(START_DATE, before_date)
    rv = ReceiptVerification(
        restaurant=restaurant,
        user=u,
        status=status,
        comment=rng.choice(comments),
        submitted_at=dt,
    )
    rv_batch.append(rv)
    rv_count += 1

with transaction.atomic():
    created_rvs = ReceiptVerification.objects.bulk_create(rv_batch, ignore_conflicts=True)
    # bulk_create는 auto_now_add를 무시하므로 submitted_at을 직접 세팅 후 update
    for rv_obj, rv_src in zip(created_rvs, rv_batch):
        if rv_obj.pk:
            ReceiptVerification.objects.filter(pk=rv_obj.pk).update(submitted_at=rv_src.submitted_at)

print(f"    → {rv_count}건 생성 시도")


# ══════════════════════════════════════════
# 3. 북마크 (Bookmark) — 44명
# ══════════════════════════════════════════
print("[3] 북마크 생성 중...")
existing_bm_users = set(
    Bookmark.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
bm_users = [u for u in dummy_users[:60] if u.id not in existing_bm_users][:44]
bm_batch = []
for u in bm_users:
    bm_batch.append(Bookmark(user=u, restaurant=restaurant))

Bookmark.objects.bulk_create(bm_batch, ignore_conflicts=True)
print(f"    → {len(bm_batch)}건 생성")


# ══════════════════════════════════════════
# 4. 리뷰 + 별점 (Review + Rating)
# ══════════════════════════════════════════
print("[4] 리뷰 & 별점 생성 중...")
review_texts = [
    "진짜 오래된 집인데 국물이 너무 맛있어요. 사골을 제대로 우린 것 같아요.",
    "점심 때 방문했는데 줄이 길었지만 기다릴 만해요. 칼국수 면이 쫄깃쫄깃해요.",
    "들깨칼국수를 처음 먹어봤는데 고소함이 엄청나네요. 국물도 깔끔하고 좋아요.",
    "가격이 착해요! 서울에서 이 가격에 이 퀄리티면 대박이죠.",
    "수제비도 시켜봤는데 둘 다 맛있었어요. 양도 푸짐하고요.",
    "위생 상태가 매우 깔끔했습니다. 테이블도 청결하고 사장님도 친절하세요.",
    "사골 국물이 진해서 속이 든든해요. 해장으로도 최고네요.",
    "동네 사람들이 자주 찾는 이유가 있는 집이에요. 기본에 충실한 맛.",
    "메뉴판 가격 그대로 받아요. 정직한 가게 느낌 확실히 받았어요.",
    "공기밥 추가해서 국물이랑 같이 먹으면 최고의 한 끼예요.",
    "재방문 꼭 할 것 같아요. 국물 맛이 집에서는 절대 못 내는 맛이에요.",
    "가성비 최고의 칼국수집이에요. 강력 추천합니다!",
    "사골 육수가 묵직하게 느껴지면서도 느끼하지 않아요. 균형이 완벽해요.",
    "점심 피크 타임에도 회전이 빨라서 오래 기다리지 않아도 됐어요.",
    "혼밥하기도 편한 구조예요. 혼자 먹어도 눈치 안 보여요.",
    "날이 추울수록 더 생각나는 집이에요. 국물이 몸을 따뜻하게 해줘요.",
    "이 집 국수 면이 직접 만드는 건지 식감이 달라요. 정말 쫄깃쫄깃.",
    "처음 왔는데 단골집 느낌이 나요. 손님 응대가 자연스럽고 편안해요.",
    "국물이 너무 짜지 않고 간이 딱 맞아요. 건강한 맛이에요.",
    "사장님이 직접 만드시는 것 같아요. 정성이 느껴지는 집이에요.",
    "주변 직장인들 사이에서 소문난 집이에요. 이제 저도 단골이 됐어요.",
    "칼국수 면이 두껍지 않고 적당해서 국물을 다 마시게 되더라고요.",
    "고명이 풍성해요. 김치랑 같이 먹으면 더 맛있어요.",
    "저는 들깨칼국수파예요. 고소한 게 중독성이 있어요.",
    "다음에도 꼭 올 거예요. 이 집 빼면 칼국수 못 먹을 것 같아요.",
    "인증된 정직 식당인 거 확인하고 왔는데, 역시 믿고 먹을 수 있는 곳이에요.",
    "위생 등급이 높다고 들었는데 실제로도 매우 깔끔했어요.",
    "혼밥, 2인 모두 편한 집이에요. 자리 배치도 좋아요.",
    "사골을 오래 끓인 티가 나요. 색깔부터 다르더라고요.",
    "가격이 안 올랐어요! 요즘 이런 집 찾기 힘든데 진짜 대단해요.",
]

existing_rv_users2 = set(
    Review.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
existing_rat_users = set(
    Rating.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)

review_users = [u for u in dummy_users if u.id not in existing_rv_users2][:min(len(review_texts), len(dummy_users))]
review_batch = []
rating_batch = []
for u, txt in zip(review_users, review_texts):
    dt = rand_dt(START_DATE, END_DATE)
    review_batch.append(Review(user=u, restaurant=restaurant, content=txt))
    if u.id not in existing_rat_users:
        score = rng.choices([5, 4, 3, 2, 1], weights=[45, 30, 15, 7, 3])[0]
        rating_batch.append(Rating(user=u, restaurant=restaurant, score=score))

with transaction.atomic():
    created_reviews = Review.objects.bulk_create(review_batch, ignore_conflicts=True)
    for rv_obj, rv_src in zip(created_reviews, review_batch):
        if rv_obj.pk:
            Review.objects.filter(pk=rv_obj.pk).update(
                created_at=rand_dt(START_DATE, END_DATE)
            )
    Rating.objects.bulk_create(rating_batch, ignore_conflicts=True)

print(f"    → 리뷰 {len(review_batch)}건, 별점 {len(rating_batch)}건 생성")


# ══════════════════════════════════════════
# 5. ReviewClassificationResult
# ══════════════════════════════════════════
print("[5] AI 리뷰 분류 결과 생성 중...")
existing_reviews = list(Review.objects.filter(restaurant=restaurant).select_related("user"))

POS_DASHBOARD_TAGS = ["맛있어요", "위생적이에요", "가성비좋아요", "재방문이에요", "친절해요", "양이많아요"]
NEG_DASHBOARD_TAGS = ["위생불량", "불친절해요", "가격비싸요", "맛없어요"]
ALLEY_TAGS_POOL    = ["현지인추천", "나만알고싶은", "단골단골"]

rcr_batch = []
for rev in existing_reviews:
    if ReviewClassificationResult.objects.filter(review=rev).exists():
        continue
    # 긍정 70% / 부정 20% / 중립 10%
    kind = rng.choices(["pos", "neg", "neu"], weights=[70, 20, 10])[0]
    if kind == "pos":
        dtags = rng.sample(POS_DASHBOARD_TAGS, k=rng.randint(1, 3))
        pos_kw = rng.sample(["위생", "재방문", "맛"], k=rng.randint(1, 2))
        neg_kw = []
    elif kind == "neg":
        dtags = rng.sample(NEG_DASHBOARD_TAGS, k=rng.randint(1, 2))
        pos_kw = []
        neg_kw = rng.sample(["위생", "응대", "가격"], k=1)
    else:
        dtags = []
        pos_kw, neg_kw = [], []

    has_alley = rng.random() < 0.20
    atags       = rng.sample(ALLEY_TAGS_POOL, k=1) if has_alley else []
    atag_scores = {t: round(rng.uniform(0.70, 0.95), 3) for t in atags}

    rcr_batch.append(ReviewClassificationResult(
        review=rev,
        status=ReviewClassificationResult.STATUS_DONE,
        alley_tags=atags,
        alley_tag_scores=atag_scores,
        dashboard_tags=dtags,
        ai_positive_keywords=pos_kw,
        ai_negative_keywords=neg_kw,
        analyzed_at=timezone.now(),
    ))

ReviewClassificationResult.objects.bulk_create(rcr_batch, ignore_conflicts=True)
print(f"    → {len(rcr_batch)}건 생성")


# ══════════════════════════════════════════
# 6. RestaurantAIProfile 생성/업데이트
# ══════════════════════════════════════════
print("[6] RestaurantAIProfile 생성/업데이트...")
profile, _ = RestaurantAIProfile.objects.get_or_create(restaurant=restaurant)
profile.positive_ratio   = 0.60
profile.negative_ratio   = 0.25
profile.ai_score_bonus   = 8
profile.ai_score_penalty = 4
profile.ai_net_score     = 4
profile.alley_review_ratio = 0.20
profile.is_alley_eligible  = False
profile.recent_hygiene_negative_ratio = 0.25
profile.hygiene_alert  = True    # 위생 경고 배너 테스트용
profile.price_match_rate  = 0.97
profile.price_match_score = 15
profile.receipt_ocr_count = 62
profile.price_is_verified = False  # 가격 경고 배너 테스트용
profile.review_count_analyzed = len(existing_reviews)
profile.last_calculated_at    = timezone.now()
profile.top_positive_tags = {
    "맛있어요":     18,
    "위생적이에요": 12,
    "가성비좋아요": 11,
    "재방문이에요": 10,
    "친절해요":     8,
}
profile.top_negative_tags = {
    "위생불량":   5,
    "가격비싸요": 4,
    "불친절해요": 3,
    "맛없어요":   2,
}
profile.dashboard_tag_summary = {**profile.top_positive_tags, **profile.top_negative_tags}
profile.save()
print(f"    → AI프로필 저장 완료 (ai_net_score={profile.ai_net_score})")


# ══════════════════════════════════════════
# 7. RestaurantAIReport 생성
# ══════════════════════════════════════════
print("[7] AI 리포트 생성 중...")
if not RestaurantAIReport.objects.filter(restaurant=restaurant, status="done").exists():
    RestaurantAIReport.objects.create(
        restaurant=restaurant,
        status="done",
        period_start=date(2026, 4, 30),
        period_end=date(2026, 5, 27),
        generated_at=timezone.now(),
        report_text=(
            "사장님, 최근 14일간 '위생'과 관련한 부정 언급이 증가했습니다. "
            "현재 부정 리뷰 비율이 25%로 신뢰 레벨 달성 위해 이 부분을 개선하실 필요가 있습니다. "
            "위생 관리 강화와 함께 영수증 인증 수집을 우선적으로 진행하시면 레벨 상승에 도움이 될 것 같습니다. "
            "긍정 리뷰는 '맛있어요', '위생적이에요', '가성비좋아요' 키워드가 상위를 차지하고 있어 주요 강점으로 보입니다."
        ),
        push_message=(
            "🔔 최근 위생 관련 부정 리뷰가 증가하고 있습니다. 지금 바로 리포트를 확인해보세요.\n"
            "⚠️ 위생 경고 발생 — 최근 14일 부정 비율 25%로 신뢰 레벨 관리가 필요합니다."
        ),
    )
    print("    → AI 리포트 생성 완료")
else:
    print("    → 이미 존재, 스킵")


# ══════════════════════════════════════════
# 8. ManagedRestaurant + SaleRecord + SaleItem
#    (2025-01-01 ~ 2026-05-27 하루 5~12건)
# ══════════════════════════════════════════
print("[8] 매출 데이터 생성 중...")
managed, _ = ManagedRestaurant.objects.get_or_create(
    public_restaurant=restaurant,
    defaults={
        "name":          restaurant.name,
        "owner_name":    "한지혜",
        "phone":         "02-123-4567",
        "address":       restaurant.address_road or "서울특별시",
        "business_type": restaurant.business_type or "한식",
        "status":        "active",
        "joined_at":     date(2025, 1, 1),
        "memo":          "더미 데이터 생성용",
    },
)

MENUS = [
    ("사골칼국수",  8000, 0.40),
    ("들깨칼국수",  9000, 0.25),
    ("수제비",      8000, 0.15),
    ("비빔국수",    8000, 0.10),
    ("공기밥",      1000, 0.20),
    ("소주",        4000, 0.18),
    ("막걸리",      5000, 0.10),
    ("콜라",        2000, 0.12),
]

existing_order_ids = set(
    SaleRecord.objects.filter(restaurant=managed).values_list("order_id", flat=True)
)

sale_records = []
sale_items   = []
cur = START_DATE
order_seq = 1

while cur <= END_DATE:
    # 주말은 주문 조금 더 많이
    is_weekend = cur.weekday() >= 5
    daily_count = rng.randint(8, 15) if is_weekend else rng.randint(5, 12)
    for _ in range(daily_count):
        oid = f"DUMMY-{cur.strftime('%Y%m%d')}-{order_seq:05d}"
        if oid in existing_order_ids:
            order_seq += 1
            continue
        hour = rng.randint(10, 20)
        minute = rng.randint(0, 59)
        dt = timezone.make_aware(datetime(cur.year, cur.month, cur.day, hour, minute))

        chosen_items = []
        total = 0
        # 메인 메뉴 1개 필수
        main_menus = [(n, p, w) for n, p, w in MENUS if p >= 8000]
        main = rng.choices(main_menus, weights=[w for _, _, w in main_menus])[0]
        chosen_items.append((main[0], 1, main[1]))
        total += main[1]
        # 사이드/음료 0~2개
        sides = [(n, p, w) for n, p, w in MENUS if p < 8000]
        num_sides = rng.choices([0, 1, 2], weights=[50, 35, 15])[0]
        for _ in range(num_sides):
            side = rng.choices(sides, weights=[w for _, _, w in sides])[0]
            qty = rng.randint(1, 2)
            chosen_items.append((side[0], qty, side[1]))
            total += side[1] * qty

        sr = SaleRecord(
            restaurant=managed,
            order_id=oid,
            amount=total,
            status="DONE",
        )
        sale_records.append((sr, dt, chosen_items))
        order_seq += 1
    cur += timedelta(days=1)

print(f"    → SaleRecord {len(sale_records)}건 생성 중 (bulk)...")
with transaction.atomic():
    sr_objs = SaleRecord.objects.bulk_create(
        [sr for sr, _, _ in sale_records], ignore_conflicts=True
    )
    # created_at 업데이트
    for obj, (_, dt, _) in zip(sr_objs, sale_records):
        if obj.pk:
            SaleRecord.objects.filter(pk=obj.pk).update(created_at=dt)

    # SaleItem 생성
    # pk가 필요하므로 다시 조회
    oid_to_pk = dict(
        SaleRecord.objects.filter(
            order_id__in=[sr.order_id for sr, _, _ in sale_records]
        ).values_list("order_id", "pk")
    )
    si_batch = []
    for sr, _, items in sale_records:
        pk = oid_to_pk.get(sr.order_id)
        if not pk:
            continue
        for menu_name, qty, price in items:
            si_batch.append(SaleItem(
                sale_record_id=pk, menu_name=menu_name, quantity=qty, price=price
            ))
    SaleItem.objects.bulk_create(si_batch, ignore_conflicts=False)

print(f"    → SaleRecord {len(sale_records)}건, SaleItem {len(si_batch)}건 생성 완료")


# ══════════════════════════════════════════
# 9. MarketingPost (오늘의 마케팅 섹션)
# ══════════════════════════════════════════
print("[9] 마케팅 포스트 생성 중...")
if not MarketingPost.objects.filter(restaurant=restaurant, owner=owner).exists():
    posts = [
        {
            "platform": "instagram",
            "status": "published",
            "input_prompt": "칼국수 맛집 홍보",
            "generated_content": "🍜 진한 사골 육수로 끓인 신목사골칼국수!\n매일 새벽부터 끓인 사골 국물로 만들어냅니다. #칼국수맛집",
            "final_content": "🍜 진한 사골 육수로 끓인 신목사골칼국수!\n매일 새벽부터 끓인 사골 국물. 오늘도 맛있게 준비했어요! 😊",
            "hashtags": ["칼국수", "사골칼국수", "정직식당", "맛집"],
            "published_at": timezone.make_aware(datetime(2026, 5, 26, 10, 51)),
        },
        {
            "platform": "instagram",
            "status": "published",
            "input_prompt": "들깨칼국수 신메뉴 소개",
            "generated_content": "🌿 고소한 들깨칼국수 드셔보셨나요?\n들깨 특유의 고소함이 사골 국물과 만나 환상의 조화를 이룹니다.",
            "final_content": "🌿 고소한 들깨칼국수 드셔보셨나요?\n한 번 드시면 자꾸 생각나는 맛! 오늘 점심은 들깨칼국수 어떠세요?",
            "hashtags": ["들깨칼국수", "칼국수", "고소한맛", "점심추천"],
            "published_at": timezone.make_aware(datetime(2026, 5, 14, 9, 12)),
        },
        {
            "platform": "naver_blog",
            "status": "published",
            "input_prompt": "정직식당 인증 소개",
            "generated_content": "안녕하세요, 신목사골칼국수입니다. 저희 가게가 정직식당 인증을 받았습니다.",
            "final_content": "안녕하세요 😊 신목사골칼국수입니다!\n이번에 정직식당 인증을 받게 되었어요. 항상 메뉴판 가격 그대로 받고 있으니 믿고 오세요!",
            "hashtags": ["정직식당", "신목사골칼국수", "칼국수"],
            "published_at": timezone.make_aware(datetime(2026, 5, 27, 18, 0)),
        },
    ]
    for p in posts:
        published_at = p.pop("published_at", None)
        mp = MarketingPost.objects.create(
            owner=owner,
            restaurant=restaurant,
            **p,
        )
        if published_at:
            MarketingPost.objects.filter(pk=mp.pk).update(
                created_at=published_at, published_at=published_at
            )
    print(f"    → 마케팅 포스트 {len(posts)}건 생성")
else:
    print("    → 이미 존재, 스킵")


# ══════════════════════════════════════════
# 10. Redis 캐시 초기화
# ══════════════════════════════════════════
print("[10] Redis 캐시 초기화...")
from django.core.cache import cache
cache.delete("index_sections")
print("    → index_sections 캐시 삭제 완료")


# ══════════════════════════════════════════
# 최종 요약
# ══════════════════════════════════════════
approved_count = ReceiptVerification.objects.filter(
    restaurant=restaurant, status=ReceiptVerification.STATUS_APPROVED
).count()
bookmark_count = restaurant.bookmarks.count()
review_count   = Review.objects.filter(restaurant=restaurant).count()
sale_count     = SaleRecord.objects.filter(restaurant=managed, status="DONE").count()

print("\n" + "="*50)
print(f"✅ 더미 데이터 생성 완료 — {restaurant.name}")
print(f"   영수증 인증(approved): {approved_count}건")
print(f"   북마크:                {bookmark_count}건")
print(f"   리뷰:                  {review_count}건")
print(f"   매출 주문:             {sale_count}건")
print("="*50)
print("→ http://127.0.0.1:8000/dashboard/ 에서 확인하세요.")
