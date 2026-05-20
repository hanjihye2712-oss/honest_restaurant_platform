from django.contrib import admin

from .models import PublicRestaurantData, ReceiptVerification


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
            "③ 위치 좌표 (중부원점TM)",
            {
                "fields": [
                    "latitude",
                    "longitude",
                ],
                "description": (
                    "⚠️ X/Y는 중부원점TM(EPSG:5174) 좌표계입니다. "
                    "WGS84 위경도가 아니므로 지도 표시 시 변환이 필요합니다."
                ),
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
        from django.utils.html import format_html, mark_safe

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
        from django.utils.html import format_html

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

@admin.register(ReceiptVerification)
class ReceiptVerificationAdmin(admin.ModelAdmin):
    list_display  = ["restaurant", "user", "status", "submitted_at"]
    list_filter   = ["status"]
    search_fields = ["restaurant__name", "user__username"]
    actions       = ["approve", "reject"]

    @admin.action(description="선택 항목 인증 승인")
    def approve(self, request, queryset):
        queryset.update(status=ReceiptVerification.STATUS_APPROVED)

    @admin.action(description="선택 항목 인증 거부")
    def reject(self, request, queryset):
        queryset.update(status=ReceiptVerification.STATUS_REJECTED)


