"""
ai_review_classifier.views
==========================
RestaurantAIProfileView  — 사장님 대시보드용 AI 집계 데이터 API
"""

from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from honest_restaurant.models import PublicRestaurantData

from .models import RestaurantAIProfile
from .tasks import recalculate_ai_profile


class RestaurantAIProfileView(APIView):
    """
    GET  /api/ai/restaurant/<pk>/profile/
    사장님 대시보드에 표시할 식당 AI 집계 데이터를 반환한다.

    권한: 스태프(is_staff=True)
    추후 사장님 자체 권한 체계 추가 시 이 뷰에서 확장한다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int) -> Response:
        if not request.user.is_staff:
            return Response({"detail": "관리자만 접근할 수 있습니다."}, status=403)

        restaurant = get_object_or_404(PublicRestaurantData, pk=pk)

        try:
            profile = restaurant.ai_profile
        except RestaurantAIProfile.DoesNotExist:
            return Response(
                {"detail": "아직 집계 데이터가 없습니다. 리뷰 분류가 완료되면 자동 생성됩니다."},
                status=404,
            )

        return Response({
            # ── 골목장인 배지 ────────────────────────────────────────
            "alley": {
                "review_ratio":  profile.alley_review_ratio,
                "is_eligible":   profile.is_alley_eligible,
                "required_ratio": 0.70,
            },
            # ── AI 점수 (레벨화 기준 10점 만점) ─────────────────────
            "ai_score": {
                "positive_ratio": profile.positive_ratio,
                "negative_ratio": profile.negative_ratio,
                "bonus":          profile.ai_score_bonus,
                "penalty":        profile.ai_score_penalty,
                "net":            profile.ai_net_score,
            },
            # ── 사장님 대시보드 태그 요약 ────────────────────────────
            "dashboard_tags": {
                "top_positive": profile.top_positive_tags,
                "top_negative": profile.top_negative_tags,
                "full_summary": profile.dashboard_tag_summary,
            },
            # ── 위생 경고 ────────────────────────────────────────────
            "hygiene_alert": {
                "is_alert":      profile.hygiene_alert,
                "recent_14d_ratio": profile.recent_hygiene_negative_ratio,
                "threshold":     0.30,
            },
            # ── 메타 ─────────────────────────────────────────────────
            "meta": {
                "review_count_analyzed": profile.review_count_analyzed,
                "last_calculated_at":    profile.last_calculated_at,
                "restaurant_name":       restaurant.name,
            },
        })


class RecalculateAIProfileView(APIView):
    """
    POST /api/ai/restaurant/<pk>/recalculate/
    스태프가 특정 식당의 AI 프로필을 수동으로 재집계 트리거한다.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int) -> Response:
        if not request.user.is_staff:
            return Response({"detail": "관리자만 접근할 수 있습니다."}, status=403)

        get_object_or_404(PublicRestaurantData, pk=pk)
        recalculate_ai_profile.delay(pk)
        return Response({"detail": f"식당 {pk} AI 프로필 재집계가 예약됐습니다."})
