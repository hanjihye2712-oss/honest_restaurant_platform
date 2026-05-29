"""
ai.ai_report.views
==================
RestaurantAIReportView     — 최신 리포트 조회
GenerateAIReportView       — 리포트 수동 생성 트리거
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from honest_restaurant.models import PublicRestaurantData
from honest_restaurant.pagination import CachedPaginator, page_range

from .models import RestaurantAIReport
from .tasks import generate_restaurant_report


class RestaurantAIReportView(APIView):
    """
    GET /api/ai/restaurant/<pk>/report/
    해당 식당의 가장 최신 완료된 리포트를 반환한다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int) -> Response:
        if not request.user.is_staff:
            return Response({"detail": "관리자만 접근할 수 있습니다."}, status=403)

        get_object_or_404(PublicRestaurantData, pk=pk)

        report = (
            RestaurantAIReport.objects
            .filter(restaurant_id=pk, status=RestaurantAIReport.STATUS_DONE)
            .order_by("-period_end")
            .first()
        )

        if not report:
            return Response(
                {"detail": "생성된 리포트가 없습니다. 먼저 리포트를 생성해주세요."},
                status=404,
            )

        return Response({
            "restaurant_id":  pk,
            "period_start":   report.period_start,
            "period_end":     report.period_end,
            "report_text":    report.report_text,
            "push_message":   report.push_message,
            "generated_at":   report.generated_at,
        })


class AIReportHistoryView(LoginRequiredMixin, View):
    """
    GET /ai/reports/history/?page=1
    로그인한 사장님 가게의 AI 리포트 전체 목록을 HTML로 반환한다.
    """

    PER_PAGE = 5

    def get(self, request):
        restaurant = getattr(request.user, "owned_restaurant", None)
        qs = RestaurantAIReport.objects.none()
        if restaurant:
            qs = (
                RestaurantAIReport.objects
                .filter(restaurant=restaurant, status=RestaurantAIReport.STATUS_DONE)
                .order_by("-period_end")
            )

        paginator = CachedPaginator(
            qs, self.PER_PAGE,
            cache_key=f"ai_report_history_{getattr(restaurant, 'pk', 0)}",
            cache_ttl=60,
        )
        page_num = int(request.GET.get("page", 1))
        page_num = max(1, min(page_num, paginator.num_pages or 1))
        page_obj = paginator.get_page(page_num)

        return render(request, "ai/report_history.html", {
            "restaurant":      restaurant,
            "page_obj":        page_obj,
            "paginator_pages": page_range(paginator, page_num),
        })


class GenerateAIReportView(APIView):
    """
    POST /api/ai/restaurant/<pk>/report/generate/
    해당 식당의 AI 리포트 생성을 Celery에 예약한다.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int) -> Response:
        if not request.user.is_staff:
            return Response({"detail": "관리자만 접근할 수 있습니다."}, status=403)

        get_object_or_404(PublicRestaurantData, pk=pk)
        generate_restaurant_report.delay(pk)

        return Response({"detail": f"식당 {pk} 리포트 생성이 예약됐습니다."})
