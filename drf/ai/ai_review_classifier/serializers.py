from rest_framework import serializers

from .models import ReviewClassificationResult


class ReviewClassificationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReviewClassificationResult
        fields = [
            "status",
            "alley_tags",
            "alley_tag_scores",
            "dashboard_tags",
            "ai_positive_keywords",
            "ai_negative_keywords",
            "analyzed_at",
        ]
