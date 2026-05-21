"""
interactions.views
==================
레이어 구분

    BookmarkViewSet  — 북마크 CRUD + toggle 액션
    RatingViewSet    — 별점 upsert (식당당 1개)
    ReviewViewSet    — 리뷰 CRUD  (식당당 1개)
    ReviewDeleteView — 리뷰 + 별점 + 영수증 인증 통합 삭제 (Axios JSON 전용)
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai.models import SentimentResult
from ai import tasks
from honest_restaurant.models import ReceiptVerification
from .models import Bookmark, Rating, Review
from .serializers import BookmarkSerializer, RatingSerializer, ReviewSerializer


# ══════════════════════════════════════════════════════════════
# 북마크 목록 페이지 (템플릿 뷰)
# ══════════════════════════════════════════════════════════════

class BookmarkListView(LoginRequiredMixin, ListView):
    """
    GET /bookmarks/
    로그인한 사용자의 북마크 목록을 렌더링한다.
    """
    template_name       = "interactions/bookmark_list.html"
    context_object_name = "bookmarks"
    paginate_by         = 20

    def get_queryset(self):
        return (
            Bookmark.objects
            .filter(user=self.request.user)
            .select_related("restaurant")
            .order_by("-created_at")
        )


class ReviewListView(LoginRequiredMixin, ListView):
    """
    GET /reviews/
    로그인한 사용자의 리뷰 목록을 렌더링한다.
    """
    template_name       = "interactions/review_list.html"
    context_object_name = "reviews"
    paginate_by         = 20

    def get_queryset(self):
        return (
            Review.objects
            .filter(user=self.request.user)
            .select_related("restaurant")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rating_map = dict(
            Rating.objects.filter(user=self.request.user).values_list("restaurant_id", "score")
        )
        for rv in ctx["reviews"]:
            rv.my_rating = rating_map.get(rv.restaurant_id)
        return ctx


# ══════════════════════════════════════════════════════════════
# BookmarkViewSet
# ══════════════════════════════════════════════════════════════

class BookmarkViewSet(viewsets.ModelViewSet):
    """
    북마크 CRUD

    기본 CRUD (list / retrieve / destroy) 외에
    toggle 액션을 주 인터페이스로 사용하도록 권장.
    """

    serializer_class   = BookmarkSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "post", "delete"]

    def get_queryset(self):
        return (
            Bookmark.objects
            .filter(user=self.request.user)
            .select_related("restaurant")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request):
        """
        POST /api/interactions/bookmarks/toggle/
        Body: { "restaurant": <id> }
        북마크가 없으면 추가, 있으면 취소.
        """
        restaurant_id = request.data.get("restaurant")
        if not restaurant_id:
            return Response(
                {"detail": "restaurant 필드가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bookmark = Bookmark.objects.filter(
            user=request.user, restaurant_id=restaurant_id
        ).first()

        if bookmark:
            bookmark.delete()
            return Response({"bookmarked": False}, status=status.HTTP_200_OK)

        Bookmark.objects.create(user=request.user, restaurant_id=restaurant_id)
        return Response({"bookmarked": True}, status=status.HTTP_201_CREATED)


# ══════════════════════════════════════════════════════════════
# RatingViewSet
# ══════════════════════════════════════════════════════════════

class RatingViewSet(viewsets.ModelViewSet):
    """
    별점 upsert — 식당당 1개 (POST가 create·update 역할을 겸함)

    POST /api/interactions/ratings/
    Body: { "restaurant": <id>, "score": 1~5 }
    """

    serializer_class   = RatingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "post", "delete"]

    def get_queryset(self):
        qs            = Rating.objects.select_related("restaurant", "user")
        restaurant_id = self.request.query_params.get("restaurant_id")
        return (
            qs.filter(restaurant_id=restaurant_id)
            if restaurant_id
            else qs.filter(user=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        restaurant_id = request.data.get("restaurant")
        raw_score     = request.data.get("score")

        if not restaurant_id:
            return Response(
                {"detail": "restaurant 필드가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            score = int(raw_score)
            if not (1 <= score <= 5):
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "score는 1~5 사이 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rating, created = Rating.objects.update_or_create(
            user=request.user,
            restaurant_id=restaurant_id,
            defaults={"score": score},
        )
        serializer = self.get_serializer(rating)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════════════════════
# ReviewViewSet
# ══════════════════════════════════════════════════════════════

class ReviewViewSet(viewsets.ModelViewSet):
    """
    리뷰 CRUD — 식당당 1개

    POST  /api/interactions/reviews/        — 작성 (이미 있으면 409)
    PATCH /api/interactions/reviews/{id}/   — 수정 (본인만)
    DELETE /api/interactions/reviews/{id}/  — 삭제 (본인만)
    """

    serializer_class   = ReviewSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        qs            = Review.objects.select_related("restaurant", "user", "sentiment")
        restaurant_id = self.request.query_params.get("restaurant_id")
        return (
            qs.filter(restaurant_id=restaurant_id)
            if restaurant_id
            else qs.filter(user=self.request.user)
        )

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user)
        SentimentResult.objects.create(review=review)
        tasks.analyze_sentiment.delay(review.id, review.content)

    def create(self, request, *args, **kwargs):
        restaurant_id = request.data.get("restaurant")
        if Review.objects.filter(
            user=request.user, restaurant_id=restaurant_id
        ).exists():
            return Response(
                {"detail": "이미 리뷰를 작성했습니다. 수정은 PATCH를 사용하세요."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """본인 리뷰만 수정 가능 (PATCH only — partial=True 강제)."""
        instance = self.get_object()
        if instance.user != request.user:
            raise PermissionDenied("권한이 없습니다.")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if "content" in serializer.validated_data:
            SentimentResult.reset_for_review(instance.id)
            tasks.analyze_sentiment.delay(instance.id, instance.content)

        return Response(serializer.data)

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("권한이 없습니다.")
        instance.delete()


# ══════════════════════════════════════════════════════════════
# ReviewDeleteView  —  통합 삭제 (리뷰 + 별점 + 영수증 인증)
# ══════════════════════════════════════════════════════════════

class ReviewDeleteView(View):
    """
    POST /api/interactions/restaurants/<pk>/review/
    Body: { "action": "delete", "review_id": <id> }

    리뷰·별점·영수증 인증을 한 트랜잭션에서 삭제.
    Axios JSON 전용 엔드포인트 (HTML form 미지원).
    """

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)

        try:
            body      = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"detail": "잘못된 요청 본문입니다."}, status=400)

        action_type = body.get("action")
        review_id   = body.get("review_id")

        if action_type != "delete":
            return JsonResponse(
                {"detail": f"지원하지 않는 action입니다: {action_type}"}, status=400
            )

        Review.objects.filter(id=review_id, user=request.user).delete()
        Rating.objects.filter(restaurant_id=pk, user=request.user).delete()
        ReceiptVerification.objects.filter(restaurant_id=pk, user=request.user).delete()

        return JsonResponse({"success": True})
