from rest_framework import serializers
from .models import Bookmark, Rating, Review


class BookmarkSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Bookmark
        fields = ["id", "restaurant", "restaurant_name", "created_at"]
        read_only_fields = ["created_at"]


class RatingSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Rating
        fields = ["id", "restaurant", "restaurant_name", "score", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "restaurant", "restaurant_name", "username", "content", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
