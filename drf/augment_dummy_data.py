"""
더미 데이터 보강 스크립트 (augment)
- 더미 유저 121~400 추가
- 리뷰 200건 이상 (리뷰 텍스트 다양화)
- 영수증 인증 500건 이상
- 북마크 날짜 2025-01~2026-05 분산 + 트렌딩 배지용 최근 30일 집중
- SentimentResult / FakeReviewResult 모든 리뷰에 생성
- 마케팅 포스트 10건 이상으로 보강
실행: python augment_dummy_data.py  (drf/ 폴더에서)
"""
import os, sys, random, django
from datetime import date, timedelta, datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from honest_restaurant.models import PublicRestaurantData, ReceiptVerification
from interactions.models import Bookmark, Review, Rating
from ai.ai_review_classifier.models import ReviewClassificationResult
from ai.ai_report.models import RestaurantAIReport
from ai.ai_sentiment.models import SentimentResult
from ai.ai_fake_review.models import FakeReviewResult
from marketing.models import MarketingPost

RESTAURANT_PK  = 866252
OWNER_USERNAME = "hanjihye"
START_DATE     = date(2025, 1, 1)
END_DATE       = date(2026, 5, 27)
rng = random.Random(2024)

def rand_dt(start: date, end: date) -> datetime:
    delta = (end - start).days
    d = start + timedelta(days=rng.randint(0, delta))
    return timezone.make_aware(datetime(d.year, d.month, d.day, rng.randint(9, 21), rng.randint(0, 59)))

def rand_recent_dt(days_ago_max: int, days_ago_min: int = 0) -> datetime:
    now = timezone.now()
    delta = rng.randint(days_ago_min * 24 * 60, days_ago_max * 24 * 60)
    return now - timedelta(minutes=delta)

restaurant = PublicRestaurantData.objects.get(pk=RESTAURANT_PK)
owner       = User.objects.get(username=OWNER_USERNAME)
print(f"[대상] {restaurant.name} (pk={restaurant.pk})")


# ══════════════════════════════════════════
# 1. 더미 유저 121~400 추가
# ══════════════════════════════════════════
print("[1] 더미 유저 121~400 생성 중...")
new_users = []
for i in range(121, 401):
    u, _ = User.objects.get_or_create(
        username=f"dummy_u{i:03d}",
        defaults={"email": f"dummy_u{i:03d}@example.com", "password": "!"},
    )
    new_users.append(u)
all_dummy = list(User.objects.filter(username__startswith="dummy_u").order_by("username"))
print(f"    → 전체 더미 유저 {len(all_dummy)}명")


# ══════════════════════════════════════════
# 2. 영수증 인증 보강 → 총 500건 이상
# ══════════════════════════════════════════
print("[2] 영수증 인증 보강 (목표 500건 approved)...")
existing_rv = set(
    ReceiptVerification.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
comments = [
    "정말 맛있었어요. 가격도 딱 메뉴판 그대로!", "사골 국물이 진해서 속이 든든해요.",
    "위생도 깔끔하고 사장님도 친절하세요.", "들깨칼국수 강추! 고소함이 최고예요.",
    "혼밥하기 딱 좋은 곳이에요.", "국수 면이 직접 뽑은 것처럼 쫄깃해요.",
    "가격 그대로 정직하게 받아요. 믿을 수 있는 가게!", "해장으로도 최고입니다.",
    "오래된 집인데 국물 맛이 변하지 않았어요.", "단골이 될 것 같아요!",
    "공기밥 추가해서 국물이랑 먹으면 최고의 한 끼.", "수제비도 정말 맛있어요.",
    "점심 피크에도 회전이 빨라서 오래 안 기다렸어요.", "양이 많아서 든든해요.",
]
rv_batch = []
needed   = 500 - ReceiptVerification.objects.filter(restaurant=restaurant, status="approved").count()
print(f"    → 추가 필요: {needed}건")

available = [u for u in all_dummy if u.id not in existing_rv]
for u in available[:needed]:
    rv_batch.append(ReceiptVerification(
        restaurant=restaurant, user=u,
        status=ReceiptVerification.STATUS_APPROVED,
        comment=rng.choice(comments),
    ))

with transaction.atomic():
    created = ReceiptVerification.objects.bulk_create(rv_batch, ignore_conflicts=True)

# 날짜 분산: 1~5개월 전 집중 (최근 방문자 인증 많은 가게)
all_rvs = list(ReceiptVerification.objects.filter(restaurant=restaurant).values_list("pk", flat=True))
# 최근 3개월에 60%, 그 이전 40%
for pk in all_rvs:
    if rng.random() < 0.60:
        dt = rand_recent_dt(90, 0)
    else:
        dt = rand_dt(START_DATE, date(2026, 2, 28))
    ReceiptVerification.objects.filter(pk=pk).update(submitted_at=dt)

approved_cnt = ReceiptVerification.objects.filter(restaurant=restaurant, status="approved").count()
print(f"    → approved 총 {approved_cnt}건")


# ══════════════════════════════════════════
# 3. 리뷰 보강 → 총 200건 이상
# ══════════════════════════════════════════
print("[3] 리뷰 보강 (목표 200건)...")
review_pool = [
    "진한 사골 국물이 일품이에요. 면도 쫄깃하고 양도 푸짐해요.",
    "들깨칼국수가 특히 고소하고 맛있어요. 재방문 확정!",
    "가격 대비 퀄리티가 정말 훌륭해요. 서울 외식물가 생각하면 착한 가격이에요.",
    "위생 상태가 정말 깔끔했어요. 테이블도 항상 청결하게 관리되고 있어요.",
    "사장님이 매우 친절하세요. 처음 방문인데 단골인 것처럼 편하게 대해줘서 좋았어요.",
    "수제비와 칼국수 반반 할 수 있나요? 다음엔 꼭 물어볼게요. 오늘은 칼국수 먹었는데 최고였어요.",
    "사골을 오래 끓인 게 느껴지는 국물이에요. 집에서는 절대 못 내는 깊은 맛.",
    "혼자 와도 눈치 안 보여요. 혼밥하기 최적의 환경이에요.",
    "점심에 줄 서서 먹었는데 기다릴 가치 있어요. 직장인 점심 맛집으로 강추!",
    "국물을 다 마셔버렸어요. 진하면서도 느끼하지 않은 게 포인트예요.",
    "비가 오는 날 칼국수 먹으러 왔는데 기분까지 따뜻해졌어요.",
    "정직식당 인증받은 곳이라 믿고 왔어요. 역시 실망 없었어요.",
    "메뉴판 가격 그대로 계산했어요. 요즘 이런 집 찾기 힘든데 정말 좋아요.",
    "공기밥은 무한 리필인 줄 알았는데 아니었지만, 양이 충분해서 괜찮아요.",
    "이 집 육수는 따로 판매해줬으면 좋겠어요. 그냥 육수만 마셔도 맛있어요.",
    "칼국수 면 두께가 딱 좋아요. 너무 얇지도, 두껍지도 않아요.",
    "오래된 가게인데 인테리어는 깔끔하게 관리되고 있어요.",
    "단골 손님들이 많이 보였어요. 그만큼 검증된 맛집이라는 뜻이죠.",
    "처음엔 간판보고 그냥 지나치다가 후기 보고 들어왔는데 이제 단골이 됐어요.",
    "수제비 반죽이 두껍지 않고 적당해서 국물이 잘 스며들어요. 맛있어요.",
    "주차가 좀 어렵지만 그래도 먹으러 올 만한 집이에요.",
    "국물이 너무 짜지 않고 딱 맞는 간이에요. 건강한 맛이라 자주 오고 싶어요.",
    "막걸리랑 같이 먹으면 더 맛있어요. 어른들 모시고 오기 좋은 집이에요.",
    "냄비 뚜껑 열리면 고소한 냄새가 확 퍼지는데 그게 너무 좋아요.",
    "빠르게 먹고 가야 하는 점심인데 음식이 빨리 나와서 좋아요.",
    "직접 반죽을 치는 건지 면이 탱탱해요. 공장 면이랑 확연히 달라요.",
    "고명이 적당히 들어가 있고, 김치도 잘 익은 게 나왔어요.",
    "식사 후 속이 편안했어요. 자극적이지 않은 맑은 국물 덕분인 것 같아요.",
    "여름에도 뜨거운 국물 땀 흘리면서 먹어도 맛있는 집이에요.",
    "서비스로 반찬이 더 나와서 감동이었어요. 다음에 또 올게요!",
    "아이랑 같이 왔는데 짜지 않아서 아이도 잘 먹었어요.",
    "국물이 묵직한 게 사골을 정말로 오래 끓인 것 같아요.",
    "정직식당 인증 받은 곳답게 믿을 수 있는 식사 자리였어요.",
    "리뷰 보고 기대하고 왔는데 기대 이상이었어요. 사장님 감사합니다!",
    "오늘 첫 방문인데 이미 단골이 됐어요. 한 달에 서너 번은 올 것 같아요.",
    "들깨칼국수와 사골칼국수를 번갈아가며 먹어요. 둘 다 맛있어요.",
    "국수 먹고 나서 국물도 다 마셔버렸어요. 죄책감 없이 다 먹은 건 오랜만이에요.",
    "친구들에게 적극 추천했어요. 다음엔 같이 올 예정이에요.",
    "어제 날씨가 쌀쌀해서 국물이 너무 먹고 싶었는데 여기서 해결했어요.",
    "사장님이 재료에 신경 많이 쓰시는 것 같아요. 국물이 맑고 진해요.",
    "근처 직장인인데 점심 때 자주 올 것 같아요. 가성비 최고!",
    "면 양이 적지 않아서 성인 남성도 배불리 먹을 수 있어요.",
    "김치가 정갈하게 나오는 게 집밥 느낌이에요.",
    "국물 따라달라고 했더니 흔쾌히 해주셨어요. 서비스 마인드가 좋아요.",
    "가게 분위기가 아늑해서 혼자 와도 편안해요.",
    "포장도 되나요? 다음엔 포장해가고 싶어요. 국물이 정말 그리울 것 같아요.",
    "이 동네에 이런 보석 같은 집이 있다는 게 행복해요.",
    "건강한 재료로 만드는 것 같아요. 맛도 맛이지만 몸에도 좋을 것 같은 느낌.",
    "칼국수 전문점답게 면이 정말 맛있어요. 다른 메뉴도 궁금해지네요.",
    "자주 와도 질리지 않는 맛이에요. 다음 주에 또 올게요!",
    "10년 전부터 다니던 가게인데 맛이 변하지 않았어요. 한결같아서 좋아요.",
    "처음 방문에 단골 결심. 주변 지인들에게 다 알려줄 거예요.",
    "국수 먹고 나니까 속이 따뜻하고 편안해요. 위가 약한 분께 추천해요.",
    "이 가격에 이 맛이면 진짜 가성비 맛집이에요.",
    "주인 할머니(?)의 손맛이 느껴지는 집이에요. 정말 맛있어요.",
    "오늘 기분이 좋아야 해서 일부러 찾아왔어요. 역시 맛있어서 기분이 좋아졌어요.",
    "매운 걸 못 먹는데 여기 칼국수는 전혀 안 매워서 좋아요.",
    "국물 한 입 마시는 순간 '왔다!' 싶었어요. 그 깊은 맛.",
    "밖에서 오래 기다렸는데 들어가서 먹으니 기다린 보람이 있었어요.",
    "항상 일정한 맛이 유지되는 게 이 집의 가장 큰 장점이에요.",
]

existing_rev_users = set(
    Review.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
existing_rat_users = set(
    Rating.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
approved_user_ids = set(
    ReceiptVerification.objects.filter(
        restaurant=restaurant,
        status__in=[ReceiptVerification.STATUS_APPROVED, ReceiptVerification.STATUS_PENDING]
    ).values_list("user_id", flat=True)
)

# 인증된 유저만 리뷰 가능
eligible = [u for u in all_dummy
            if u.id in approved_user_ids
            and u.id not in existing_rev_users]

target_new = max(0, 210 - Review.objects.filter(restaurant=restaurant).count())
writers    = eligible[:target_new]
rev_batch  = []
rat_batch  = []
for u in writers:
    rev_batch.append(Review(user=u, restaurant=restaurant, content=rng.choice(review_pool)))
    if u.id not in existing_rat_users:
        score = rng.choices([5, 4, 3, 2, 1], weights=[45, 33, 14, 5, 3])[0]
        rat_batch.append(Rating(user=u, restaurant=restaurant, score=score))

with transaction.atomic():
    created_revs = Review.objects.bulk_create(rev_batch, ignore_conflicts=True)
    Rating.objects.bulk_create(rat_batch, ignore_conflicts=True)

# 리뷰 날짜 분산
all_rev_pks = list(Review.objects.filter(restaurant=restaurant).values_list("pk", flat=True))
for pk in all_rev_pks:
    dt = rand_dt(START_DATE, END_DATE)
    Review.objects.filter(pk=pk).update(created_at=dt)

print(f"    → 리뷰 총 {Review.objects.filter(restaurant=restaurant).count()}건")


# ══════════════════════════════════════════
# 4. 북마크 날짜 분산 + 트렌딩 배지 보강
#    - 전체 분산: 2025-01 ~ 2026-04
#    - 최근 30일에 35개 이상 집중 (트렌딩 조건: curr >= 30)
#    - 31~60일 전에 10개 (증가율 200% 이상)
# ══════════════════════════════════════════
print("[4] 북마크 보강 및 날짜 분산...")

# 북마크 추가 (총 120건 목표)
existing_bm_users = set(
    Bookmark.objects.filter(restaurant=restaurant).values_list("user_id", flat=True)
)
bm_add = [u for u in all_dummy if u.id not in existing_bm_users]
bm_needed = max(0, 120 - Bookmark.objects.filter(restaurant=restaurant).count())
bm_batch  = [Bookmark(user=u, restaurant=restaurant) for u in bm_add[:bm_needed]]
Bookmark.objects.bulk_create(bm_batch, ignore_conflicts=True)

# 날짜 분산
all_bm = list(Bookmark.objects.filter(restaurant=restaurant).order_by("pk"))
total_bm = len(all_bm)

# 최근 30일: 40개 → 트렌딩 curr >= 30
# 31~60일 전: 12개 → prev = 12, curr/prev = 40/12 = 333% > 200% → 인기급상승 배지 활성화
# 나머지: 2025-01 ~ 2026-03 분산
recent_30_count  = 40
prev_30_count    = 12
old_count        = total_bm - recent_30_count - prev_30_count

rng.shuffle(all_bm)
buckets = (
    [(bm, "recent") for bm in all_bm[:recent_30_count]]
    + [(bm, "prev")  for bm in all_bm[recent_30_count:recent_30_count + prev_30_count]]
    + [(bm, "old")   for bm in all_bm[recent_30_count + prev_30_count:]]
)

for bm, bucket in buckets:
    if bucket == "recent":
        dt = rand_recent_dt(29, 0)
    elif bucket == "prev":
        dt = rand_recent_dt(60, 31)
    else:
        dt = rand_dt(START_DATE, date(2026, 3, 31))
    Bookmark.objects.filter(pk=bm.pk).update(created_at=dt)

from django.utils import timezone as tz
from datetime import timedelta
now = tz.now()
curr = Bookmark.objects.filter(restaurant=restaurant, created_at__gte=now - timedelta(days=30)).count()
prev = Bookmark.objects.filter(
    restaurant=restaurant,
    created_at__gte=now - timedelta(days=60),
    created_at__lt=now - timedelta(days=30)
).count()
total_bm_now = Bookmark.objects.filter(restaurant=restaurant).count()
print(f"    → 북마크 총 {total_bm_now}건  최근30일:{curr}개  전30일:{prev}개  증가율:{round(curr/prev*100) if prev else '∞'}%")


# ══════════════════════════════════════════
# 5. SentimentResult / FakeReviewResult 생성
# ══════════════════════════════════════════
print("[5] SentimentResult / FakeReviewResult 생성 중...")

all_reviews = list(Review.objects.filter(restaurant=restaurant))

SENTIMENT_LABELS = ["positive", "negative", "neutral"]
sent_batch  = []
fake_batch  = []
for rev in all_reviews:
    # SentimentResult
    if not SentimentResult.objects.filter(review=rev).exists():
        label = rng.choices(SENTIMENT_LABELS, weights=[60, 20, 20])[0]
        sent_batch.append(SentimentResult(
            review=rev,
            status=SentimentResult.STATUS_DONE,
            label=label,
            score=round(rng.uniform(0.65, 0.98), 3),
            analyzed_at=timezone.now(),
        ))
    # FakeReviewResult
    if not FakeReviewResult.objects.filter(review=rev).exists():
        is_fake = rng.random() < 0.08
        fake_batch.append(FakeReviewResult(
            review=rev,
            status=FakeReviewResult.STATUS_DONE,
            is_fake=is_fake,
            confidence=round(rng.uniform(0.70, 0.99), 3),
            penalty_score=FakeReviewResult.PENALTY_FAKE if is_fake else 0,
            analyzed_at=timezone.now(),
        ))

SentimentResult.objects.bulk_create(sent_batch, ignore_conflicts=True)
FakeReviewResult.objects.bulk_create(fake_batch, ignore_conflicts=True)
print(f"    → SentimentResult {len(sent_batch)}건, FakeReviewResult {len(fake_batch)}건 생성")


# ══════════════════════════════════════════
# 6. ReviewClassificationResult 보강
# ══════════════════════════════════════════
print("[6] ReviewClassificationResult 보강 중...")
POS_TAGS  = ["맛있어요", "위생적이에요", "가성비좋아요", "재방문이에요", "친절해요", "양이많아요", "고소해요"]
NEG_TAGS  = ["위생불량", "불친절해요", "가격비싸요", "맛없어요", "대기길어요"]
ALLEY_TAGS_POOL = ["현지인추천", "나만알고싶은", "단골단골"]

rcr_batch = []
for rev in all_reviews:
    if ReviewClassificationResult.objects.filter(review=rev, status="done").exists():
        continue
    kind = rng.choices(["pos", "neg", "neu"], weights=[65, 20, 15])[0]
    if kind == "pos":
        dtags  = rng.sample(POS_TAGS, k=rng.randint(1, 3))
        pos_kw = rng.sample(["위생", "재방문", "맛", "친절"], k=rng.randint(1, 2))
        neg_kw = []
    elif kind == "neg":
        dtags  = rng.sample(NEG_TAGS, k=rng.randint(1, 2))
        pos_kw = []
        neg_kw = rng.sample(["위생", "응대", "가격"], k=1)
    else:
        dtags, pos_kw, neg_kw = [], [], []

    has_alley   = rng.random() < 0.18
    atags       = rng.sample(ALLEY_TAGS_POOL, k=1) if has_alley else []
    atag_scores = {t: round(rng.uniform(0.70, 0.95), 3) for t in atags}

    rcr_batch.append(ReviewClassificationResult(
        review=rev,
        status=ReviewClassificationResult.STATUS_DONE,
        alley_tags=atags, alley_tag_scores=atag_scores,
        dashboard_tags=dtags,
        ai_positive_keywords=pos_kw, ai_negative_keywords=neg_kw,
        analyzed_at=timezone.now(),
    ))

ReviewClassificationResult.objects.bulk_create(rcr_batch, ignore_conflicts=True)
print(f"    → {len(rcr_batch)}건 추가")


# ══════════════════════════════════════════
# 7. RestaurantAIProfile 재계산
# ══════════════════════════════════════════
print("[7] AI 프로필 재계산...")
from ai.ai_review_classifier.models import RestaurantAIProfile
profile = RestaurantAIProfile.objects.get(restaurant=restaurant)

done_rcrs = list(
    ReviewClassificationResult.objects.filter(
        review__restaurant=restaurant, status="done"
    ).values("dashboard_tags", "alley_tags", "ai_positive_keywords", "ai_negative_keywords")
)
total_rcr = len(done_rcrs)

pos_cnt = sum(1 for r in done_rcrs if r["ai_positive_keywords"])
neg_cnt = sum(1 for r in done_rcrs if r["ai_negative_keywords"])
alley_cnt = sum(1 for r in done_rcrs if r["alley_tags"])

profile.positive_ratio = round(pos_cnt / total_rcr, 3) if total_rcr else 0
profile.negative_ratio = round(neg_cnt / total_rcr, 3) if total_rcr else 0
profile.alley_review_ratio = round(alley_cnt / total_rcr, 3) if total_rcr else 0
profile.is_alley_eligible  = alley_cnt / total_rcr >= 0.15 if total_rcr else False

# 태그 빈도 집계
from collections import Counter
all_tags = []
for r in done_rcrs:
    all_tags.extend(r["dashboard_tags"])
tag_counter = Counter(all_tags)
pos_tag_keys = set(POS_TAGS)
neg_tag_keys = set(NEG_TAGS)
profile.top_positive_tags = dict(sorted(
    {k: v for k, v in tag_counter.items() if k in pos_tag_keys}.items(),
    key=lambda x: -x[1]
)[:5])
profile.top_negative_tags = dict(sorted(
    {k: v for k, v in tag_counter.items() if k in neg_tag_keys}.items(),
    key=lambda x: -x[1]
)[:5])
profile.dashboard_tag_summary = dict(tag_counter.most_common(10))

# AI 점수
bonus   = round(profile.positive_ratio * 10)
penalty = round(profile.negative_ratio * 10)
net     = min(10, max(-10, bonus - penalty))
profile.ai_score_bonus   = bonus
profile.ai_score_penalty = penalty
profile.ai_net_score     = net
profile.review_count_analyzed = total_rcr
profile.recent_hygiene_negative_ratio = round(
    sum(1 for r in done_rcrs if "위생불량" in r["dashboard_tags"]) / total_rcr, 3
) if total_rcr else 0
profile.hygiene_alert = profile.recent_hygiene_negative_ratio >= 0.10
profile.price_match_rate  = 0.97
profile.price_match_score = 15
profile.receipt_ocr_count = ReceiptVerification.objects.filter(
    restaurant=restaurant, status="approved"
).count()
profile.price_is_verified = profile.receipt_ocr_count >= 30
profile.last_calculated_at = timezone.now()
profile.save()

print(f"    → ai_net_score={net:+d}, 긍정비율={round(profile.positive_ratio*100)}%, "
      f"골목장인={profile.is_alley_eligible}, 위생경고={profile.hygiene_alert}")


# ══════════════════════════════════════════
# 8. 마케팅 포스트 보강 (총 10건 이상)
# ══════════════════════════════════════════
print("[8] 마케팅 포스트 보강...")
existing_posts = MarketingPost.objects.filter(restaurant=restaurant).count()
extra_posts = [
    {
        "platform": "instagram", "status": "published",
        "input_prompt": "주말 특별 메뉴 홍보",
        "generated_content": "🌿 주말에는 특별히 더 진하게 끓인 사골 국물을 준비했어요!",
        "final_content": "🌿 주말 특별 사골칼국수!\n매주 금요일 밤부터 48시간 끓인 특제 사골 국물. 이번 주말도 신목사골칼국수에서 만나요 😊",
        "hashtags": ["사골칼국수", "주말맛집", "칼국수"],
        "days_ago": 10,
    },
    {
        "platform": "naver_blog", "status": "published",
        "input_prompt": "단골 감사 이벤트",
        "generated_content": "저희 식당을 자주 찾아주시는 단골 손님들께 감사 인사를 드립니다.",
        "final_content": "항상 찾아주시는 소중한 손님들께 진심으로 감사드립니다. 앞으로도 변함없는 맛과 서비스로 보답하겠습니다!",
        "hashtags": ["신목사골칼국수", "단골감사", "칼국수맛집"],
        "days_ago": 18,
    },
    {
        "platform": "kakao_story", "status": "published",
        "input_prompt": "들깨칼국수 소개",
        "generated_content": "고소한 들깨향이 가득한 들깨칼국수를 소개합니다.",
        "final_content": "🌾 들깨칼국수 아시나요?\n구수하고 고소한 들깨 국물과 쫄깃한 칼국수 면의 조화. 한 번 드셔보시면 반드시 또 오시게 됩니다!",
        "hashtags": ["들깨칼국수", "고소한맛", "칼국수"],
        "days_ago": 30,
    },
    {
        "platform": "instagram", "status": "published",
        "input_prompt": "봄 시즌 홍보",
        "generated_content": "봄이 왔어요! 따뜻한 칼국수 한 그릇으로 봄을 맞이해요.",
        "final_content": "🌸 봄 기운 물씬!\n따사로운 봄 햇살 아래 따뜻한 사골칼국수 한 그릇. 어떠세요? 오늘 점심, 신목사골칼국수로 오세요!",
        "hashtags": ["봄칼국수", "봄점심", "칼국수맛집", "신목사골칼국수"],
        "days_ago": 45,
    },
    {
        "platform": "naver_blog", "status": "published",
        "input_prompt": "정직한 가격 소개",
        "generated_content": "저희는 메뉴판에 적힌 가격 그대로 받습니다. 추가 요금 없이 정직하게 운영합니다.",
        "final_content": "신목사골칼국수의 약속: 메뉴판 가격 그대로!\n저희는 어떤 상황에서도 메뉴판 가격 이상을 받지 않습니다. 정직한 가격으로 맛있는 칼국수를 제공하겠습니다.",
        "hashtags": ["정직식당", "착한가격", "신목사골칼국수"],
        "days_ago": 60,
    },
    {
        "platform": "instagram", "status": "published",
        "input_prompt": "영수증 인증 고객 감사",
        "generated_content": "영수증 인증해 주신 소중한 고객님들, 감사합니다!",
        "final_content": "💌 영수증 인증해주신 고객님들께 감사드려요!\n정직식당 인증을 위해 영수증 인증에 참여해 주신 모든 분들 덕분에 저희가 더 성장할 수 있어요. 항상 감사합니다!",
        "hashtags": ["정직식당", "영수증인증", "신목사골칼국수"],
        "days_ago": 75,
    },
    {
        "platform": "kakao_story", "status": "published",
        "input_prompt": "겨울 해장 메뉴 홍보",
        "generated_content": "쌀쌀한 겨울, 따뜻한 해장 국물 한 그릇으로 속을 달래세요.",
        "final_content": "🥶 추운 날씨, 속을 달래줄 해장 메뉴!\n진한 사골 국물이 차가운 속을 따뜻하게 녹여줘요. 해장으로도 최고인 신목사골칼국수!",
        "hashtags": ["해장칼국수", "겨울맛집", "사골해장"],
        "days_ago": 120,
    },
]

for p in extra_posts:
    days_ago     = p.pop("days_ago")
    published_at = timezone.now() - timedelta(days=days_ago)
    mp = MarketingPost.objects.create(
        owner=owner, restaurant=restaurant, **p,
    )
    MarketingPost.objects.filter(pk=mp.pk).update(
        created_at=published_at, published_at=published_at,
    )

print(f"    → 총 {MarketingPost.objects.filter(restaurant=restaurant).count()}건")


# ══════════════════════════════════════════
# 9. AI 리포트 최신화
# ══════════════════════════════════════════
print("[9] AI 리포트 최신화...")
RestaurantAIReport.objects.filter(restaurant=restaurant, status="done").update(
    report_text=(
        f"사장님, 최근 14일간 '위생'과 관련한 부정 언급이 증가했습니다. "
        f"현재 부정 리뷰 비율이 {round(profile.negative_ratio*100)}%로 신뢰 레벨 달성 위해 이 부분을 개선하실 필요가 있습니다. "
        f"위생 관리 강화와 함께 영수증 인증 수집을 우선적으로 진행하시면 레벨 상승에 도움이 될 것 같습니다. "
        f"긍정 리뷰는 '{'·'.join(list(profile.top_positive_tags.keys())[:3])}' 키워드가 상위를 차지하고 있어 주요 강점으로 보입니다."
    )
)
print("    → 완료")


# ══════════════════════════════════════════
# 10. Redis 캐시 초기화
# ══════════════════════════════════════════
from django.core.cache import cache
cache.delete("index_sections")
print("[10] Redis 캐시 초기화 완료")


# ══════════════════════════════════════════
# 최종 요약
# ══════════════════════════════════════════
from honest_restaurant.views import _calc_level_score

approved_cnt = ReceiptVerification.objects.filter(restaurant=restaurant, status="approved").count()
bm_total     = Bookmark.objects.filter(restaurant=restaurant).count()
now2         = timezone.now()
curr_bm = Bookmark.objects.filter(restaurant=restaurant, created_at__gte=now2 - timedelta(days=30)).count()
prev_bm = Bookmark.objects.filter(restaurant=restaurant, created_at__gte=now2 - timedelta(days=60), created_at__lt=now2 - timedelta(days=30)).count()
sd = _calc_level_score(restaurant, profile)

print("\n" + "="*55)
print(f"✅ 데이터 보강 완료 — {restaurant.name}")
print(f"   영수증 인증(approved): {approved_cnt}건")
print(f"   북마크:                {bm_total}건  (최근30일:{curr_bm} / 전30일:{prev_bm})")
print(f"   리뷰:                  {Review.objects.filter(restaurant=restaurant).count()}건")
print(f"   SentimentResult:       {SentimentResult.objects.filter(review__restaurant=restaurant).count()}건")
print(f"   FakeReviewResult:      {FakeReviewResult.objects.filter(review__restaurant=restaurant).count()}건")
print(f"   마케팅 포스트:         {MarketingPost.objects.filter(restaurant=restaurant).count()}건")
print()
print(f"   레벨 점수: {sd['total']}/100 → LV{sd['level']} {sd['level_name']}")
print(f"     정부인증   {sd['govt_score']:2}/25  |  가격일치율 {sd['price_score']:2}/20")
print(f"     방문자인증 {sd['visit_score']:2}/15  |  찜수       {sd['like_score']:2}/10")
print(f"     연혁       {sd['history_score']:2}/20  |  AI점수    {sd['ai_score']:2}/10")
trending = curr_bm >= 30 and prev_bm > 0 and (curr_bm / prev_bm * 100) >= 200
print(f"   트렌딩 배지: {'✅ 활성화' if trending else '❌ 비활성'}")
print("="*55)
