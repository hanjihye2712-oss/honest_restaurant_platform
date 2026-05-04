from django.shortcuts import render
from django.core.paginator import Paginator
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import PublicRestaurantData
from .serializers import PublicRestaurantDataSerializer


# ════════════════════════════════════════════════
# 1) API 뷰셋 (JSON 응답 — 기존 코드 유지)
# ════════════════════════════════════════════════

class PublicRestaurantDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    서울시 공공 식당 데이터 JSON API
    - list     : GET /api/public-restaurants/
    - retrieve : GET /api/public-restaurants/{id}/
    """

    queryset = PublicRestaurantData.objects.filter(
        status_code=PublicRestaurantData.STATUS_OPEN
    )
    serializer_class = PublicRestaurantDataSerializer

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["district", "business_type", "sanitation_business_type"]
    search_fields    = ["name", "address_road", "category_name"]
    ordering_fields  = ["license_date", "name", "synced_at"]
    ordering         = ["-synced_at"]


# ════════════════════════════════════════════════
# 2) 템플릿 뷰 (HTML 응답 — 임시 페이지용)
# ════════════════════════════════════════════════

def restaurant_list_page(request):
    """
    템플릿 기반 식당 목록 페이지
    - GET /restaurants/                    → 전체 목록
    - GET /restaurants/?district=종로구    → 자치구 필터
    - GET /restaurants/?business_type=한식 → 업태 필터
    - GET /restaurants/?search=김밥        → 이름·주소 검색
    """

    qs = PublicRestaurantData.objects.filter(
        status_code=PublicRestaurantData.STATUS_OPEN
    )

    # ── 쿼리 파라미터 파싱 ──────────────────────
    search        = request.GET.get("search", "").strip()
    district      = request.GET.get("district", "").strip()
    business_type = request.GET.get("business_type", "").strip()

    # ── 필터 적용 ───────────────────────────────
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(address_road__icontains=search) |
            Q(category_name__icontains=search)
        )

    if district:
        qs = qs.filter(district=district)

    if business_type:
        qs = qs.filter(business_type=business_type)

    # ── 페이지네이션 (한 페이지 20개) ──────────
    paginator   = Paginator(qs.order_by("-synced_at"), 20)
    page_number = request.GET.get("page", 1)
    restaurants = paginator.get_page(page_number)

    # ── 필터 드롭다운용 선택지 ──────────────────
    # values_list + distinct → DB에 있는 값만 동적으로 노출
    district_choices = (
        PublicRestaurantData.objects
        .filter(status_code=PublicRestaurantData.STATUS_OPEN)
        .exclude(district="")
        .values_list("district", flat=True)
        .distinct()
        .order_by("district")
    )
    business_type_choices = (
        PublicRestaurantData.objects
        .filter(status_code=PublicRestaurantData.STATUS_OPEN)
        .exclude(business_type="")
        .values_list("business_type", flat=True)
        .distinct()
        .order_by("business_type")
    )

    # ── 페이지네이션 링크에 기존 파라미터 유지 ──
    # ex) ?search=김밥&district=종로구 (page= 제외)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    context = {
        "restaurants"          : restaurants,
        "total_count"          : paginator.count,
        "district_choices"     : district_choices,
        "business_type_choices": business_type_choices,
        "query_string"         : query_string,
    }
    return render(request, "restaurants/restaurant_list.html", context)