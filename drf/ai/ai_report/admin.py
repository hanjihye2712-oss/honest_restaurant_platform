from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html

from ai.admin_utils import DEFAULT_BADGE, badge
from .models import AIReportConfig, RestaurantAIReport
from .tasks import generate_restaurant_report


@admin.register(AIReportConfig)
class AIReportConfigAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'temperature', 'report_period_days']

    fieldsets = [
        ('모델 설정', {
            'fields': ['model_name', 'temperature', 'report_period_days'],
            'description': 'AI 모델명과 창의성 수준(Temperature)을 설정합니다. Temperature: 0=일정, 2=창의적',
        }),
        ('프롬프트 설정', {
            'fields': ['role_description', 'writing_rules'],
            'description': 'role_description에서 {period_days} 는 분석 기간(일)으로 자동 치환됩니다.',
        }),
    ]

    def has_add_permission(self, request):
        return not AIReportConfig.objects.exists()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.delete('ai_report_config')

STATUS_STYLE = {
    RestaurantAIReport.STATUS_DONE:    ("#d4edda", "#155724", "생성 완료"),
    RestaurantAIReport.STATUS_PENDING: ("#fff3cd", "#856404", "생성 대기"),
    RestaurantAIReport.STATUS_FAILED:  ("#f8d7da", "#721c24", "생성 실패"),
}


@admin.register(RestaurantAIReport)
class RestaurantAIReportAdmin(admin.ModelAdmin):
    list_display  = [
        "restaurant_name", "period_display", "status_badge",
        "push_message_preview", "generated_at",
    ]
    list_filter   = ["status"]
    search_fields = ["restaurant__name"]
    ordering      = ["-period_end"]
    readonly_fields = [
        "restaurant", "status_badge", "period_display",
        "report_text", "push_message", "generated_at", "error_msg",
    ]
    fieldsets = [
        ("식당 정보",   {"fields": ["restaurant", "period_display"]}),
        ("리포트 내용", {"fields": ["status_badge", "report_text", "push_message", "generated_at"]}),
        ("오류 정보",   {"fields": ["error_msg"], "classes": ["collapse"]}),
    ]
    actions = ["regenerate_reports"]

    @admin.display(description="식당명")
    def restaurant_name(self, obj):
        return obj.restaurant.name

    @admin.display(description="분석 기간")
    def period_display(self, obj):
        return f"{obj.period_start} ~ {obj.period_end}"

    @admin.display(description="상태")
    def status_badge(self, obj):
        bg, color, label = STATUS_STYLE.get(obj.status, (*DEFAULT_BADGE, obj.status))
        return badge(bg, color, label)

    @admin.display(description="푸시 알림 미리보기")
    def push_message_preview(self, obj):
        if not obj.push_message:
            return "—"
        preview = obj.push_message[:60]
        return preview + "…" if len(obj.push_message) > 60 else preview

    @admin.action(description="선택 식당 리포트 재생성")
    def regenerate_reports(self, request, queryset):
        count = 0
        for report in queryset:
            generate_restaurant_report.delay(report.restaurant_id)
            count += 1
        self.message_user(request, f"{count}개 식당 리포트 재생성을 예약했습니다.")
