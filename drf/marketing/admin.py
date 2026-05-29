from django.contrib import admin
from django.core.cache import cache
from .models import MarketingPost, MarketingPlatformConfig, MarketingAIConfig


def _clear_marketing_cache():
    cache.delete('mkt_platform_configs')
    cache.delete('mkt_ai_config')


@admin.register(MarketingPlatformConfig)
class MarketingPlatformConfigAdmin(admin.ModelAdmin):
    list_display  = ['order', 'display_name', 'platform', 'guide', 'is_active']
    list_editable = ['order', 'is_active']
    list_display_links = ['display_name']
    ordering = ['order']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _clear_marketing_cache()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        _clear_marketing_cache()


@admin.register(MarketingAIConfig)
class MarketingAIConfigAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'temperature']

    fieldsets = [
        ('모델 설정', {
            'fields': ['model_name', 'temperature'],
            'description': '사용할 Gemini 모델명과 창의성 수준(Temperature)을 설정합니다. Temperature: 0=일정, 2=창의적',
        }),
        ('프롬프트 설정', {
            'fields': ['role_description', 'writing_instruction'],
            'description': (
                'writing_instruction에서 {platform} 은 플랫폼명으로 자동 치환됩니다.'
            ),
        }),
    ]

    def has_add_permission(self, request):
        return not MarketingAIConfig.objects.exists()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _clear_marketing_cache()


@admin.register(MarketingPost)
class MarketingPostAdmin(admin.ModelAdmin):
    list_display  = ['id', 'restaurant', 'platform', 'status', 'scheduled_at', 'published_at', 'created_at']
    list_filter   = ['platform', 'status']
    search_fields = ['restaurant__name', 'final_content']
    readonly_fields = ['generated_content', 'published_at', 'created_at', 'updated_at']

    fieldsets = [
        ('기본 정보', {
            'fields': ['owner', 'restaurant', 'platform', 'status'],
        }),
        ('입력 & 생성 내용', {
            'fields': ['input_prompt', 'generated_content', 'final_content', 'hashtags'],
        }),
        ('발행 정보', {
            'fields': ['scheduled_at', 'published_at', 'external_post_id'],
        }),
        ('기록', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]
