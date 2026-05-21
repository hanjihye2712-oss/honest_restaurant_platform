from rest_framework import serializers
from .models import FakeReviewResult


class FakeReviewResultSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FakeReviewResult
        fields = ["status", "is_fake", "confidence", "analyzed_at"]
