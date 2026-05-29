"""
사장님 대시보드 테스트용 더미 데이터 주입 커맨드.

사용법:
  python manage.py seed_dashboard_demo                  # 현재 owner 계정 자동 탐색
  python manage.py seed_dashboard_demo --username=jihye # 특정 사용자
  python manage.py seed_dashboard_demo --scenario=lv2   # 시나리오 선택
  python manage.py seed_dashboard_demo --reset          # 데이터 초기화
"""

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

User = get_user_model()

SCENARIOS = {
    "lv3": {
        "label": "LV3 신뢰 (68점) — 프리뷰 기준",
        "ai_profile": {
            "positive_ratio": 0.82,
            "negative_ratio": 0.08,
            "ai_net_score": 6,
            "ai_score_bonus": 6,
            "ai_score_penalty": 0,
            "alley_review_ratio": 0.73,
            "is_alley_eligible": True,
            "price_match_rate": 0.95,
            "price_match_score": 15,
            "price_is_verified": True,
            "receipt_ocr_count": 45,
            "review_count_analyzed": 87,
            "hygiene_alert": False,
            "top_positive_tags": {
                "맛있어요": 124,
                "위생적이에요": 89,
                "재방문 의사": 67,
                "친절해요": 53,
                "제가 좋음": 38,
            },
            "top_negative_tags": {
                "양이 적어요": 31,
                "대기 길어요": 18,
                "주차 불편": 12,
                "위생 우려": 9,
                "환경 비좁음": 6,
            },
        },
        "ai_report": {
            "report_text": (
                "사장님, 최근 3개월간 '손님 만족도'가 42% 상승하며 점심 회전율이 크게 높아졌습니다. "
                "다만, 최근 2주간 '양이 적어졌다'는 의견이 15% 증가하고 있으니 기본 제공량을 점검해 보세요!"
            ),
            "push_message": (
                "📊 월 푸시 알림 미리보기\n"
                "'손님 만족도' 42% 상승! 그런데 양 관련 불만이 늘고 있어요. 리포트를 확인하세요."
            ),
        },
        "receipt_count": 45,
        "bookmark_count": 12,
    },
    "lv2": {
        "label": "LV2 우수 신뢰 (78점)",
        "ai_profile": {
            "positive_ratio": 0.88,
            "negative_ratio": 0.05,
            "ai_net_score": 8,
            "ai_score_bonus": 8,
            "ai_score_penalty": 0,
            "alley_review_ratio": 0.80,
            "is_alley_eligible": True,
            "price_match_rate": 1.0,
            "price_match_score": 20,
            "price_is_verified": True,
            "receipt_ocr_count": 68,
            "review_count_analyzed": 130,
            "hygiene_alert": False,
            "top_positive_tags": {
                "맛있어요": 210,
                "위생적이에요": 185,
                "재방문 의사": 140,
                "현지인 추천": 120,
                "친절해요": 95,
            },
            "top_negative_tags": {
                "대기 길어요": 12,
                "주차 불편": 8,
                "가격 아쉬움": 5,
            },
        },
        "ai_report": {
            "report_text": (
                "사장님, 지난 한 달간 '현지인 추천' 키워드가 35% 증가하며 골목장인 배지 유지에 크게 기여하고 있습니다. "
                "가격 일치율이 100%로 최고 수준을 유지 중이며, 꾸준한 영수증 인증이 신뢰 레벨을 높이고 있습니다."
            ),
            "push_message": (
                "🏅 골목장인 배지 유지 중!\n"
                "이번 주 방문 인증 5건이 새로 등록되었어요. 이 추세라면 다음 달 LV1 달성이 가능합니다."
            ),
        },
        "receipt_count": 120,
        "bookmark_count": 35,
    },
    "lv4": {
        "label": "LV4 탐색 중 (38점) — 알림 경고 포함",
        "ai_profile": {
            "positive_ratio": 0.60,
            "negative_ratio": 0.25,
            "ai_net_score": -4,
            "ai_score_bonus": 0,
            "ai_score_penalty": 4,
            "alley_review_ratio": 0.20,
            "is_alley_eligible": False,
            "price_match_rate": 0.65,
            "price_match_score": 0,
            "price_is_verified": False,
            "receipt_ocr_count": 8,
            "review_count_analyzed": 23,
            "hygiene_alert": True,
            "top_positive_tags": {
                "맛있어요": 18,
                "친절해요": 12,
            },
            "top_negative_tags": {
                "위생 우려": 31,
                "불친절": 18,
                "대기 길어요": 14,
                "양이 적어요": 9,
                "가격 아쉬움": 6,
            },
        },
        "ai_report": {
            "report_text": (
                "사장님, 최근 14일간 '위생'과 관련된 부정 언급이 급격히 증가했습니다. "
                "현재 부정 리뷰 비율이 25%로 신뢰 레벨 강등 위험이 있습니다. "
                "위생 관리 점검과 함께 영수증 인증 수집을 우선적으로 진행하시길 권장합니다."
            ),
            "push_message": (
                "⚠️ 위생 경고 발생\n"
                "최근 부정 리뷰가 급증 중입니다. 지금 바로 리뷰를 확인해보세요."
            ),
        },
        "receipt_count": 5,
        "bookmark_count": 2,
    },
}


class Command(BaseCommand):
    help = "사장님 대시보드 테스트용 더미 데이터를 주입합니다."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="대상 사용자명 (미지정 시 첫 owner 계정)")
        parser.add_argument(
            "--scenario",
            type=str,
            default="lv3",
            choices=list(SCENARIOS.keys()),
            help="테스트 시나리오 (lv3/lv2/lv4, 기본값: lv3)",
        )
        parser.add_argument("--reset", action="store_true", help="주입한 더미 데이터 초기화")

    def handle(self, *args, **options):
        from honest_restaurant.models import PublicRestaurantData, ReceiptVerification
        from interactions.models import Bookmark
        from ai.ai_review_classifier.models import RestaurantAIProfile
        from ai.ai_report.models import RestaurantAIReport

        # ── 1. 대상 레스토랑 찾기 ───────────────────────────────────
        username = options.get("username")
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"사용자 '{username}'를 찾을 수 없습니다.")
            restaurant = getattr(user, "owned_restaurant", None)
            if not restaurant:
                raise CommandError(f"'{username}'에 연결된 매장이 없습니다.")
        else:
            # owner role을 가진 첫 번째 사용자의 가게
            from accounts.models import UserProfile
            owner_profile = (
                UserProfile.objects.filter(role="owner")
                .select_related("user__owned_restaurant")
                .first()
            )
            if not owner_profile:
                raise CommandError("owner 계정이 없습니다. --username 옵션을 사용하거나 관리자에서 owner 계정을 만드세요.")
            user = owner_profile.user
            restaurant = getattr(user, "owned_restaurant", None)
            if not restaurant:
                raise CommandError(f"'{user.username}'에 연결된 매장이 없습니다.")

        self.stdout.write(f"대상 매장: {restaurant.name} (pk={restaurant.pk})")

        # ── 2. 초기화 모드 ────────────────────────────────────────
        if options["reset"]:
            self._reset(restaurant, user, RestaurantAIProfile, RestaurantAIReport, ReceiptVerification, Bookmark)
            return

        # ── 3. 시나리오 로드 ─────────────────────────────────────
        scenario_key = options["scenario"]
        scenario = SCENARIOS[scenario_key]
        self.stdout.write(f"시나리오: {scenario['label']}")

        # ── 4. AI 프로필 업서트 ──────────────────────────────────
        ai_data = scenario["ai_profile"]
        ai_profile, created = RestaurantAIProfile.objects.update_or_create(
            restaurant=restaurant,
            defaults={**ai_data, "last_calculated_at": timezone.now()},
        )
        action = "생성" if created else "업데이트"
        self.stdout.write(self.style.SUCCESS(f"  ✓ AI 프로필 {action}"))

        # ── 5. AI 리포트 생성 ─────────────────────────────────────
        today = date.today()
        report_data = scenario["ai_report"]
        RestaurantAIReport.objects.filter(restaurant=restaurant).delete()
        RestaurantAIReport.objects.create(
            restaurant=restaurant,
            status=RestaurantAIReport.STATUS_DONE,
            report_text=report_data["report_text"],
            push_message=report_data["push_message"],
            period_start=today - timedelta(days=37),
            period_end=today - timedelta(days=7),
            generated_at=timezone.now(),
        )
        self.stdout.write(self.style.SUCCESS("  ✓ AI 리포트 생성"))

        # ── 6. 영수증 인증 더미 추가 ─────────────────────────────
        # UNIQUE (restaurant, user) 제약 → 가상 테스트 유저를 사용
        target_count = scenario["receipt_count"]
        existing_count = restaurant.verifications.filter(
            status=ReceiptVerification.STATUS_APPROVED
        ).count()
        to_create = max(0, target_count - existing_count)

        if to_create > 0:
            now = timezone.now()
            sample_comments = [
                "가성비 최고!",
                "또 방문할게요",
                "영수증 직접 찍었습니다",
                "음식이 맛있어요",
                "위생 상태 좋습니다",
                "사장님 친절해요",
                "자주 올게요",
                "",
            ]

            # 이미 해당 가게를 인증한 유저 PK 제외
            used_user_ids = set(
                restaurant.verifications.values_list("user_id", flat=True)
            )

            # 기존 데모 유저 재활용 + 필요 시 신규 생성
            demo_users = []
            for i in range(to_create):
                uname = f"_demo_rv_{i:04d}"
                try:
                    u = User.objects.get(username=uname)
                except User.DoesNotExist:
                    u = User.objects.create_user(
                        username=uname,
                        password=None,
                        is_active=False,
                    )
                if u.pk not in used_user_ids:
                    demo_users.append(u)
                    used_user_ids.add(u.pk)

            verifications = []
            for i, du in enumerate(demo_users):
                verifications.append(
                    ReceiptVerification(
                        restaurant=restaurant,
                        user=du,
                        status=ReceiptVerification.STATUS_APPROVED,
                        comment=sample_comments[i % len(sample_comments)],
                    )
                )

            objs = ReceiptVerification.objects.bulk_create(verifications, ignore_conflicts=True)

            # submitted_at(auto_now_add) 을 과거 날짜로 분산
            for idx, obj in enumerate(objs):
                if obj.pk:
                    ReceiptVerification.objects.filter(pk=obj.pk).update(
                        submitted_at=now - timedelta(days=idx % 180, hours=idx % 24)
                    )
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ 영수증 인증 {len(verifications)}건 추가 (총 {existing_count + len(verifications)}건)"
            ))
        else:
            self.stdout.write(f"  - 영수증 인증 이미 {existing_count}건 (추가 생략)")

        # ── 7. 찜(북마크) 더미 추가 ─────────────────────────────
        bm_target = scenario["bookmark_count"]
        existing_bm = restaurant.bookmarks.count()
        to_bm = max(0, bm_target - existing_bm)

        if to_bm > 0:
            now = timezone.now()
            staff_users = list(User.objects.filter(is_staff=True)[:to_bm])
            if not staff_users:
                staff_users = [user]

            bms = []
            for i in range(min(to_bm, len(staff_users))):
                bms.append(Bookmark(restaurant=restaurant, user=staff_users[i]))
            if bms:
                Bookmark.objects.bulk_create(bms, ignore_conflicts=True)
                self.stdout.write(self.style.SUCCESS(f"  ✓ 찜 {len(bms)}건 추가"))
        else:
            self.stdout.write(f"  - 찜 이미 {existing_bm}건 (추가 생략)")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"완료! 대시보드 확인: http://127.0.0.1:8000/dashboard/"
        ))

    def _reset(self, restaurant, user, RestaurantAIProfile, RestaurantAIReport, ReceiptVerification, Bookmark):
        RestaurantAIProfile.objects.filter(restaurant=restaurant).delete()
        RestaurantAIReport.objects.filter(restaurant=restaurant).delete()
        deleted_rv, _ = ReceiptVerification.objects.filter(restaurant=restaurant, user=user).delete()
        Bookmark.objects.filter(restaurant=restaurant, user=user).delete()
        self.stdout.write(self.style.WARNING(
            f"초기화 완료 — AI 프로필/리포트 삭제, 영수증 인증 {deleted_rv}건 삭제"
        ))
