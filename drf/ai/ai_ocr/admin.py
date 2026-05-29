from django.contrib import admin
from django.utils.html import format_html

from ai.admin_utils import badge
from honest_restaurant.models import ReceiptVerification, RestaurantMenuItem
from .tasks import analyze_receipt


@admin.register(RestaurantMenuItem)
class RestaurantMenuItemAdmin(admin.ModelAdmin):
    list_display  = ["restaurant_name", "name", "price_display", "created_at"]
    list_filter   = ["restaurant"]
    search_fields = ["restaurant__name", "name"]
    ordering      = ["restaurant__name", "name"]

    @admin.display(description="식당명")
    def restaurant_name(self, obj):
        return obj.restaurant.name

    @admin.display(description="가격")
    def price_display(self, obj):
        return f"{obj.price:,}원"


@admin.register(ReceiptVerification)
class ReceiptVerificationOCRAdmin(admin.ModelAdmin):
    list_display  = [
        "restaurant_name", "user", "status",
        "price_match_display", "ocr_items_count", "ocr_analyzed_at",
    ]
    list_filter   = ["status"]
    search_fields = ["restaurant__name", "user__username"]
    ordering      = ["-submitted_at"]
    readonly_fields = [
        "restaurant", "user", "status", "receipt_image_preview",
        "price_match_display", "extracted_items",
        "price_discrepancies_display", "ocr_analyzed_at",
    ]
    fieldsets = [
        ("인증 정보",  {"fields": ["restaurant", "user", "status", "receipt_image_preview"]}),
        ("가격 비교",  {"fields": ["price_match_display", "price_discrepancies_display"]}),
        ("OCR 결과",  {"fields": ["extracted_items", "ocr_analyzed_at"]}),
    ]
    actions = ["reanalyze_receipts"]

    @admin.display(description="식당명")
    def restaurant_name(self, obj):
        return obj.restaurant.name

    @admin.display(description="가격 일치율")
    def price_match_display(self, obj):
        if obj.price_match_rate is None:
            return badge("#e9ecef", "#495057", "비교 불가")
        pct = obj.price_match_rate * 100
        if obj.price_match_rate >= 1.0:
            return badge("#d4edda", "#155724", "100% 일치")
        if obj.price_match_rate >= 0.90:
            return badge("#fff3cd", "#856404", f"{pct:.0f}% 일치")
        return badge("#f8d7da", "#721c24", f"⚠️ {pct:.0f}% 일치")

    @admin.display(description="OCR 항목 수")
    def ocr_items_count(self, obj):
        count = len(obj.extracted_items)
        return f"{count}개" if count else "—"

    @admin.display(description="영수증 이미지")
    def receipt_image_preview(self, obj):
        if not obj.receipt_image:
            return "—"
        return format_html(
            '<img src="{}" style="max-height:200px;max-width:400px;border-radius:4px;">',
            obj.receipt_image.url,
        )

    @admin.display(description="가격 불일치 항목")
    def price_discrepancies_display(self, obj):
        if not obj.price_discrepancies:
            return "—"
        rows = []
        for d in obj.price_discrepancies:
            rows.append(
                f'<tr><td>{d["menu"]}</td>'
                f'<td>{d["menu_price"]:,}원</td>'
                f'<td style="color:#dc3545;font-weight:600;">{d["receipt_price"]:,}원</td>'
                f'<td style="color:#dc3545;">+{d["diff"]:,}원</td></tr>'
            )
        table = (
            '<table style="border-collapse:collapse;font-size:13px;">'
            '<tr style="background:#f8f9fa;"><th style="padding:4px 8px;">메뉴</th>'
            '<th style="padding:4px 8px;">등록가</th>'
            '<th style="padding:4px 8px;">영수증</th>'
            '<th style="padding:4px 8px;">차액</th></tr>'
            + "".join(rows)
            + "</table>"
        )
        return format_html(table)

    @admin.action(description="선택 영수증 재분석")
    def reanalyze_receipts(self, request, queryset):
        count = 0
        for v in queryset:
            if v.receipt_image:
                analyze_receipt.delay(v.pk)
                count += 1
        self.message_user(request, f"{count}개 영수증 재분석을 예약했습니다.")
