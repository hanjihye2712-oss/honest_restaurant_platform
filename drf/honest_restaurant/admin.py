from django.contrib import admin
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from .models import PublicRestaurantData, RestaurantOwnerApplication


@admin.register(PublicRestaurantData)
class PublicRestaurantDataAdmin(admin.ModelAdmin):

    # ── 목록 화면 ─────────────────────────────────
    list_display = [
        "name",
        "business_type",
        "status_badge",
        "cert_badges",
        "operating_years",
        "is_veteran_store",
        "synced_at",
    ]

    list_filter = [
        "status_code",
        "business_type",
        "is_excellent_restaurant",
        "is_ansim_restaurant",
        "is_goodprice_shop",
    ]

    search_fields = [
        "name",                  # 업소명
        "address_road",          # 도로명주소
        "address_jibun",         # 지번주소
        "management_no",         # 관리번호
        "phone",
    ]

    ordering = ["-synced_at"]

    # 한 페이지 표시 건수
    list_per_page = 50

    # 읽기 전용 필드 (공공 API 원본 데이터이므로 수정 불필요)
    readonly_fields = [
        "management_no",
        "synced_at",
        "created_at",
        "operating_years",
        "is_veteran_store",
        "is_open",
    ]

    # ── 상세 화면 레이아웃 ──────────────────────────
    fieldsets = [
        (
            "① 가게 식별 / 기본 정보",
            {
                "fields": [
                    "management_no",
                    "name",
                    "address_road",
                    "address_jibun",
                    "phone",
                    "business_type",
                    "category_name",
                ],
            },
        ),
        (
            "② 정부 인증 / 위생 정보",
            {
                "fields": [
                    "sanitation_business_type",
                    "license_date",
                    "status_code",
                    "area",
                    "last_modified_at",
                ],
            },
        ),
        (
            "⑤ 위생등급 (식품안전나라 C004)",
            {
                "fields": [
                    "hygiene_grade",
                    "hygiene_grade_no",
                    "hygiene_grade_from",
                    "hygiene_grade_to",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "⑥ 모범음식점 (행정안전부)",
            {
                "fields": [
                    "is_excellent_restaurant",
                    "excellent_dsgn_ymd",
                    "excellent_re_dsgn_ymd",
                    "excellent_food_type",
                    "excellent_main_menu",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "③ 위치 좌표 (WGS84)",
            {
                "fields": [
                    "latitude",
                    "longitude",
                ],
                "description": (
                    "동기화 시 중부원점TM(EPSG:5174) → WGS84(EPSG:4326)로 변환해 저장됩니다. "
                    "지도 표시에 바로 사용 가능합니다."
                ),
            },
        ),
        (
            "⑧ SNS 계정 연동",
            {
                "fields": ["sns_connected"],
                "description": "체크 시 마케팅 관리 페이지에 예약/즉시 발행 기능이 활성화됩니다.",
            },
        ),
        (
            "④ 자동 계산 / 동기화 정보",
            {
                "fields": [
                    "is_open",
                    "operating_years",
                    "is_veteran_store",
                    "synced_at",
                    "created_at",
                ],
                "classes": ["collapse"],   # 기본 접힘
            },
        ),
    ]

    # ── 커스텀 컬럼: 정부 인증 배지 ───────────────
    @admin.display(description="정부 인증")
    def cert_badges(self, obj):
        badges = []
        if obj.hygiene_grade:
            badges.append(
                '<span style="background:#d1ecf1;color:#0c5460;padding:2px 7px;'
                'border-radius:999px;font-size:11px;margin-right:3px;">위생</span>'
            )
        if obj.is_excellent_restaurant:
            badges.append(
                '<span style="background:#d4edda;color:#155724;padding:2px 7px;'
                'border-radius:999px;font-size:11px;margin-right:3px;">모범</span>'
            )
        if obj.is_ansim_restaurant:
            badges.append(
                '<span style="background:#cce5ff;color:#004085;padding:2px 7px;'
                'border-radius:999px;font-size:11px;margin-right:3px;">안심</span>'
            )
        if obj.is_goodprice_shop:
            badges.append(
                '<span style="background:#fff3cd;color:#856404;padding:2px 7px;'
                'border-radius:999px;font-size:11px;margin-right:3px;">착한가격</span>'
            )
        return mark_safe("".join(badges)) if badges else "—"

    # ── 커스텀 컬럼: 영업상태를 색깔 배지로 표시 ──
    @admin.display(description="영업상태")
    def status_badge(self, obj):
        color_map = {
            PublicRestaurantData.STATUS_OPEN      : ("#d4edda", "#155724", "영업"),
            PublicRestaurantData.STATUS_SUSPENDED : ("#fff3cd", "#856404", "휴업"),
            PublicRestaurantData.STATUS_CLOSED    : ("#f8d7da", "#721c24", "폐업"),
        }

        # status_code에 해당하는 색상/텍스트 가져오기, 없으면 기본값
        bg, text_color, label = color_map.get(
            obj.status_code,
            ("#e9ecef", "#495057", obj.status_code)   # 알 수 없는 코드
        )

        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:999px;font-size:12px;">{}</span>',
            bg,          # {} 첫 번째
            text_color,  # {} 두 번째
            label,       # {} 세 번째
        )





# ── 사업자 인증 신청 Admin ────────────────────────────────────────────────

@admin.register(RestaurantOwnerApplication)
class RestaurantOwnerApplicationAdmin(admin.ModelAdmin):

    list_display    = ["restaurant", "user", "business_number", "verify_type_badge", "status_badge", "cert_preview", "applied_at"]
    list_filter     = ["status", "verified_by_api"]
    search_fields   = ["restaurant__name", "user__username", "business_number"]
    readonly_fields = ["restaurant", "user", "business_number", "verified_by_api", "cert_preview_large", "applied_at"]
    actions         = ["approve", "reject"]

    def verify_type_badge(self, obj):
        if obj.verified_by_api:
            return mark_safe(
                '<span style="background:#cce5ff;color:#004085;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700">국세청 API ✓</span>'
            )
        return mark_safe(
            '<span style="background:#e2e3e5;color:#383d41;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700">서류 제출</span>'
        )
    verify_type_badge.short_description = "인증 방식"

    def status_badge(self, obj):
        colors = {
            "pending":  ("#fff3cd", "#856404", "검토 중"),
            "approved": ("#d4edda", "#155724", "승인"),
            "rejected": ("#f8d7da", "#721c24", "반려"),
        }
        bg, fg, label = colors.get(obj.status, ("#eee", "#333", obj.status))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700">{}</span>',
            bg, fg, label,
        )
    status_badge.short_description = "상태"

    def cert_preview(self, obj):
        if obj.cert_image:
            return format_html('<img src="{}" style="height:48px;border-radius:4px">', obj.cert_image.url)
        return mark_safe('<span style="color:#aaa;font-size:12px">없음 (API 인증)</span>')
    cert_preview.short_description = "사업자등록증"

    def cert_preview_large(self, obj):
        if obj.cert_image:
            return format_html('<img src="{}" style="max-width:400px;border:1px solid #ccc">', obj.cert_image.url)
        return "사업자등록증 미첨부 (국세청 API로 계속사업자 확인됨)"
    cert_preview_large.short_description = "사업자등록증 원본"

    @admin.action(description="✅ 선택한 신청 승인 — 사장님 권한 부여")
    def approve(self, request, queryset):
        count = 0
        for app in queryset.filter(status=RestaurantOwnerApplication.STATUS_PENDING):
            restaurant = app.restaurant
            if restaurant.owner is not None:
                continue
            with transaction.atomic():
                restaurant.owner = app.user
                restaurant.save(update_fields=["owner"])
                profile = app.user.profile
                profile.role = "owner"
                profile.save(update_fields=["role"])
                app.status      = RestaurantOwnerApplication.STATUS_APPROVED
                app.reviewed_at = timezone.now()
                app.save(update_fields=["status", "reviewed_at"])
            count += 1
        self.message_user(request, f"{count}건 승인 완료 — 사장님 권한이 부여됐습니다.")

    @admin.action(description="❌ 선택한 신청 반려")
    def reject(self, request, queryset):
        count = queryset.filter(status=RestaurantOwnerApplication.STATUS_PENDING).update(
            status=RestaurantOwnerApplication.STATUS_REJECTED,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{count}건 반려 완료.")
