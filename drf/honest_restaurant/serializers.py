"""
honest_restaurant.serializers
==============================
PublicRestaurantDataSerializer       — 목록 API용 (집계 필드 포함)
PublicRestaurantDataDetailSerializer — 상세 API용 (+ 리뷰 목록)

N+1 방지 전략
    ViewSet queryset에 prefetch_related("bookmarks", "ratings", "interaction_reviews")
    설정되어 있으므로 SerializerMethodField에서 .all()을 사용하면 캐시 활용.
    .count() / .aggregate()는 prefetch 캐시를 우회해 N+1이 발생하므로 사용 금지.
"""

from rest_framework import serializers

from .models import PublicRestaurantData


# ──────────────────────────────────────────────────────────────
# 공통 Mixin — interactions 집계 필드
# ──────────────────────────────────────────────────────────────

class InteractionFieldsMixin:
    """
    북마크 / 별점 / 리뷰 집계 필드.
    prefetch_related 된 related manager를 순회하므로 N+1 쿼리가 없음.
    """

    def get_is_bookmarked(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        uid = request.user.id
        return any(b.user_id == uid for b in obj.bookmarks.all())

    def get_bookmark_count(self, obj) -> int:
        return len(obj.bookmarks.all())

    def get_avg_rating(self, obj):
        scores = [r.score for r in obj.ratings.all()]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 1)

    def get_rating_count(self, obj) -> int:
        return len(obj.ratings.all())

    def get_review_count(self, obj) -> int:
        return len(obj.interaction_reviews.all())


# ──────────────────────────────────────────────────────────────
# 목록 API 시리얼라이저
# ──────────────────────────────────────────────────────────────

class PublicRestaurantDataSerializer(InteractionFieldsMixin,
                                     serializers.ModelSerializer):
    """
    GET /api/public-restaurants/
    모델 프로퍼티와 interactions 집계 필드를 함께 노출.
    management_no (내부 식별자)는 응답에서 제외.
    """

    # 모델 프로퍼티
    is_open          = serializers.BooleanField(read_only=True)
    operating_years  = serializers.FloatField(read_only=True)
    is_veteran_store = serializers.BooleanField(read_only=True)

    # interactions 집계 (N+1 없음 — prefetch 캐시 사용)
    is_bookmarked  = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    avg_rating     = serializers.SerializerMethodField()
    rating_count   = serializers.SerializerMethodField()
    review_count   = serializers.SerializerMethodField()

    class Meta:
        model  = PublicRestaurantData
        fields = [
            # 기본 정보
            "id", "name",
            "address_road", "address_jibun",
            "province", "phone",
            "business_type", "category_name",
            # 인허가 / 위생
            "sanitation_business_type",
            "license_date", "status_code", "area", "last_modified_at",
            # 좌표
            "latitude", "longitude",
            # 관리 메타
            "synced_at", "created_at",
            # 프로퍼티
            "is_open", "operating_years", "is_veteran_store",
            # interactions 집계
            "is_bookmarked", "bookmark_count",
            "avg_rating", "rating_count", "review_count",
        ]
        # management_no는 응답 노출 불필요 — 필드 목록에서 아예 제외


# ──────────────────────────────────────────────────────────────
# 상세 API 시리얼라이저
# ──────────────────────────────────────────────────────────────

class PublicRestaurantDataDetailSerializer(PublicRestaurantDataSerializer):
    """
    GET /api/public-restaurants/{id}/
    목록 시리얼라이저에 리뷰 목록을 추가.
    목록에서는 리뷰 전체를 내려주면 페이로드가 크므로 retrieve에서만 사용.
    """

    reviews = serializers.SerializerMethodField()

    def get_reviews(self, obj):
        from interactions.serializers import ReviewSerializer
        qs = obj.interaction_reviews.select_related("user").order_by("-created_at")
        return ReviewSerializer(qs, many=True).data

    class Meta(PublicRestaurantDataSerializer.Meta):
        fields = PublicRestaurantDataSerializer.Meta.fields + ["reviews"]
