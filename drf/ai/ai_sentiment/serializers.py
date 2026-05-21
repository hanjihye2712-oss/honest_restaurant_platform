from rest_framework import serializers
from .models import SentimentResult


class SentimentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SentimentResult
        fields = ["status", "label", "score", "analyzed_at"]
