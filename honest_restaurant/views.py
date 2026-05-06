from django.shortcuts import render, get_object_or_404
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

def index_page(request):
    return render(request, 'restaurants/index.html')


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
            Q(address_jibun__icontains=search) |
            Q(category_name__icontains=search) |
            Q(district__icontains=search) |
            Q(business_type__icontains=search)
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


def restaurant_detail_page(request, pk):
    from .models import Review, ReceiptVerification
    from .forms import ReviewForm
    from django.shortcuts import redirect

    restaurant = get_object_or_404(PublicRestaurantData, pk=pk)
    reviews = restaurant.reviews.select_related("author").all()

    has_verified = (
        request.user.is_authenticated
        and ReceiptVerification.objects.filter(
            restaurant=restaurant,
            user=request.user,
            status=ReceiptVerification.STATUS_APPROVED,
        ).exists()
    )

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")
        if not has_verified:
            form = ReviewForm()
        else:
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.restaurant = restaurant
                review.author = request.user
                review.save()
                return redirect("public_restaurants:restaurant-detail-page", pk=pk)
    else:
        form = ReviewForm()

    context = {
        "restaurant": restaurant,
        "reviews": reviews,
        "form": form,
        "has_verified": has_verified,
    }
    return render(request, "restaurants/restaurant_detail.html", context)


def receipt_verify_page(request, pk):
    from .models import ReceiptVerification
    from .forms import ReceiptVerificationForm
    from django.shortcuts import redirect

    restaurant = get_object_or_404(PublicRestaurantData, pk=pk)

    if not request.user.is_authenticated:
        return redirect("login")

    existing = ReceiptVerification.objects.filter(
        restaurant=restaurant, user=request.user
    ).first()

    if request.method == "POST":
        form = ReceiptVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.restaurant = restaurant
            verification.user = request.user
            verification.status = ReceiptVerification.STATUS_PENDING
            if existing:
                existing.receipt_image = verification.receipt_image
                existing.comment = verification.comment
                existing.status = ReceiptVerification.STATUS_PENDING
                existing.save()
            else:
                verification.save()
            return redirect("public_restaurants:restaurant-detail-page", pk=pk)
    else:
        form = ReceiptVerificationForm()

    return render(request, "restaurants/restaurant_verify.html", {
        "restaurant": restaurant,
        "form": form,
        "existing": existing,
    })


def media_upload(request, pk):
    from .models import RestaurantMedia
    from .forms import RestaurantMediaForm
    from django.shortcuts import redirect
    import os

    if not request.user.is_authenticated:
        return redirect("login")

    restaurant = get_object_or_404(PublicRestaurantData, pk=pk)

    if request.method == "POST":
        form = RestaurantMediaForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            media_type = (
                RestaurantMedia.TYPE_VIDEO
                if ext in [".mp4", ".mov", ".avi", ".webm"]
                else RestaurantMedia.TYPE_IMAGE
            )
            RestaurantMedia.objects.create(
                restaurant=restaurant,
                uploaded_by=request.user,
                file=uploaded_file,
                media_type=media_type,
            )

    return redirect("public_restaurants:restaurant-detail-page", pk=pk)


def media_delete(request, pk, media_pk):
    from .models import RestaurantMedia
    from django.shortcuts import redirect
    import os

    if not request.user.is_authenticated:
        return redirect("login")

    media = get_object_or_404(RestaurantMedia, pk=media_pk, restaurant__pk=pk)
    if media.uploaded_by == request.user or request.user.is_staff:
        if media.file and os.path.isfile(media.file.path):
            os.remove(media.file.path)
        media.delete()

    return redirect("public_restaurants:restaurant-detail-page", pk=pk)