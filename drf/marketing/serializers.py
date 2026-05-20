from rest_framework import serializers
from .models import MarketingPost


class MarketingPostSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display',   read_only=True)

    class Meta:
        model  = MarketingPost
        fields = [
            'id',
            'restaurant',
            'input_prompt',
            'generated_content',
            'final_content',
            'hashtags',
            'platform',
            'platform_display',
            'status',
            'status_display',
            'scheduled_at',
            'published_at',
            'external_post_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['generated_content', 'published_at', 'external_post_id', 'created_at', 'updated_at']


class GenerateRequestSerializer(serializers.Serializer):
    """AI 글 생성 요청 — FastAPI로 넘길 데이터"""
    restaurant_id = serializers.IntegerField()
    input_prompt  = serializers.CharField()
    platform      = serializers.ChoiceField(choices=MarketingPost.PLATFORM_CHOICES)


class PublishRequestSerializer(serializers.Serializer):
    """발행 요청"""
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
