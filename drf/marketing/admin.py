from django.contrib import admin
from .models import MarketingPost


@admin.register(MarketingPost)
class MarketingPostAdmin(admin.ModelAdmin):
    list_display  = ['id', 'restaurant', 'platform', 'status', 'scheduled_at', 'published_at', 'created_at']
    list_filter   = ['platform', 'status']
    search_fields = ['restaurant__name', 'final_content']
    readonly_fields = ['generated_content', 'published_at', 'created_at', 'updated_at']
