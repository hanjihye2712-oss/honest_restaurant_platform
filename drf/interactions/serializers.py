from rest_framework import serializers

from ai.ai_sentiment.models import SentimentResult
from ai.ai_sentiment.serializers import SentimentResultSerializer
from ai.ai_fake_review.models import FakeReviewResult
from ai.ai_fake_review.serializers import FakeReviewResultSerializer
from .models import Bookmark, Rating, Review


class BookmarkSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model  = Bookmark
        fields = ["id", "restaurant", "restaurant_name", "created_at"]
        read_only_fields = ["created_at"]


class RatingSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model  = Rating
        fields = ["id", "restaurant", "restaurant_name", "score", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ReviewSerializer(serializers.ModelSerializer):
    username        = serializers.CharField(source="user.username", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    sentiment       = serializers.SerializerMethodField()
    fake_review     = serializers.SerializerMethodField()

    class Meta:
        model  = Review
        fields = [
            "id", "restaurant", "restaurant_name", "username",
            "content", "sentiment", "fake_review", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_sentiment(self, obj):
        try:
            return SentimentResultSerializer(obj.sentiment).data
        except SentimentResult.DoesNotExist:
            return None

    def get_fake_review(self, obj):
        try:
            return FakeReviewResultSerializer(obj.fake_review).data
        except FakeReviewResult.DoesNotExist:
            return None
