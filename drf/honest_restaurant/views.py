"""
honest_restaurant.views
=======================
레이어 구분
    RestaurantViewSet    — DRF ReadOnly JSON API
    IndexView            — 메인 페이지 (TemplateView)
    RestaurantListView   — 목록 페이지 (ListView)
    RestaurantDetailView — 상세 페이지 (DetailView)
    DistrictListView     — 구/군 목록 API
    MapMarkersView       — 지도 마커 API
    ReceiptVerifyView    — 영수증 업로드
    VerifyCancelView     — 이탈 시 인증 취소 beacon 처리
    MediaUploadView      — 미디어 업로드
    MediaDeleteView      — 미디어 삭제

외부 API 동기화 서비스는 services.py 에서 관리한다.
페이지네이션 관련 클래스·함수는 pagination.py 에서 관리한다.
"""

import hashlib
import json
import logging
import os
from datetime import date

import requests
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from rest_framework import filters, viewsets
from django_filters.rest_framework import DjangoFilterBackend

from .forms import ReceiptVerificationForm, RestaurantMediaForm
from .models import PublicRestaurantData, ReceiptVerification, RestaurantMedia
from .pagination import CachedPaginator, RestaurantCursorPagination, page_range
from .serializers import (
    PublicRestaurantDataDetailSerializer,
    PublicRestaurantDataSerializer,
)
from interactions.models import Bookmark, Rating, Review


# ══════════════════════════════════════════════════════════════
# DRF ViewSet  —  JSON API
# ══════════════════════════════════════════════════════════════
# 공통 헬퍼
# ══════════════════════════════════════════════════════════════

def _apply_restaurant_filters(qs, params, *, include_category=False):
    """search/province/district/business_type/min_years/cert/bounds 파라미터로 쿼리셋 필터링."""
    search         = params.get("search",    "").strip()
    province       = params.get("province",  "").strip()
    district       = params.get("district",  "").strip()
    min_years      = params.get("min_years", "").strip()
    certs          = [v for v in params.getlist("cert") if v.strip()]
    business_types = [v for v in params.getlist("business_type") if v.strip()]
    sw_lat         = params.get("sw_lat",    "").strip()
    sw_lng         = params.get("sw_lng",    "").strip()
    ne_lat         = params.get("ne_lat",    "").strip()
    ne_lng         = params.get("ne_lng",    "").strip()

    for token in search.split():
        q = (
            Q(name__icontains=token)
            | Q(address_road__icontains=token)
            | Q(address_jibun__icontains=token)
            | Q(province__icontains=token)
            | Q(business_type__icontains=token)
        )
        if include_category:
            q |= Q(category_name__icontains=token)
        qs = qs.filter(q)

    if province:
        qs = qs.filter(
            Q(address_road__startswith=province) |
            Q(address_jibun__startswith=province)
        )
    if district:
        qs = qs.filter(
            Q(address_road__icontains=district) |
            Q(address_jibun__icontains=district)
        )
    if business_types:
        qs = qs.filter(business_type__in=business_types)
    if certs:
        today = date.today()
        if 'excellent' in certs:
            qs = qs.filter(is_excellent_restaurant=True)
        if 'hygiene' in certs:
            qs = qs.filter(hygiene_grade__isnull=False, hygiene_grade_to__gte=today).exclude(hygiene_grade='')
        if 'ansim' in certs:
            qs = qs.filter(is_ansim_restaurant=True)
        if 'goodprice' in certs:
            qs = qs.filter(is_goodprice_shop=True)
    if min_years:
        try:
            today     = date.today()
            threshold = today.replace(year=today.year - int(min_years))
            qs = qs.filter(license_date__isnull=False, license_date__lte=threshold)
        except (ValueError, TypeError):
            pass
    if all([sw_lat, sw_lng, ne_lat, ne_lng]):
        try:
            qs = qs.filter(
                longitude__gte=float(sw_lng), longitude__lte=float(ne_lng),
                latitude__gte=float(sw_lat),  latitude__lte=float(ne_lat),
            )
        except (ValueError, TypeError):
            pass
    return qs


# ══════════════════════════════════════════════════════════════

class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    전국 공공 식당 데이터 Read-only API

    GET  /api/public-restaurants/       — 목록 (cursor 페이지네이션)
    GET  /api/public-restaurants/{id}/  — 상세 (+ 리뷰 목록)
    """

    queryset = (
        PublicRestaurantData.objects
        .filter(status_code=PublicRestaurantData.STATUS_OPEN)
        .prefetch_related("bookmarks", "ratings", "interaction_reviews")
    )
    pagination_class = RestaurantCursorPagination          # cursor 페이지네이션 적용
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["province", "business_type", "sanitation_business_type"]
    search_fields    = ["name", "address_road", "category_name"]
    ordering_fields  = ["license_date", "name", "synced_at"]
    ordering         = ["-synced_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicRestaurantDataDetailSerializer
        return PublicRestaurantDataSerializer


# ══════════════════════════════════════════════════════════════
# Template Views  —  HTML 페이지
# ══════════════════════════════════════════════════════════════

class IndexView(TemplateView):
    template_name = "honest_restaurant/index.html"

    def get(self, request, *args, **kwargs):
        # /?owner=1 로 직접 접근하면 전용 페이지로 리다이렉트
        if request.GET.get('owner') == '1':
            return redirect('public_restaurants:owner-dashboard')
        return super().get(request, *args, **kwargs)


class OwnerDashboardView(LoginRequiredMixin, TemplateView):
    """
    GET /dashboard/
    사장님·관리자 전용 대시보드 페이지.
    로그인하지 않은 경우 로그인 페이지로 이동한다.
    """
    template_name = "honest_restaurant/owner_dashboard.html"
    login_url     = "/accounts/login/"

    def handle_no_permission(self):
        return redirect(f"{self.login_url}?next=/dashboard/")


class RestaurantListView(ListView):
    """
    GET /restaurants/
    Query params: ?search= ?province= ?business_type= ?page=

    성능 최적화 포인트
    ─────────────────────────────────────────────────────────
    1. Subquery bookmark_count
       COUNT("bookmarks") 는 전체 테이블 JOIN+GROUP BY → 느림.
       Subquery는 페이지에 출력되는 20건에만 서브쿼리를 실행 → 빠름.

    2. defer() 미사용 컬럼 제외
       SELECT 에서 불필요한 컬럼을 빼 DB→Python 데이터 전송량 감소.

    3. CachedPaginator COUNT 캐시 (5분)
       COUNT(*)는 필터가 같으면 캐시를 재사용해 불필요한 집계 쿼리 제거.

    4. _MAX_PAGE 제한
       극단적 OFFSET (페이지 500 = OFFSET 9980) 을 차단해
       악의적 요청으로 인한 DB 부하를 방지.
    """

    template_name       = "honest_restaurant/restaurant_list.html"
    context_object_name = "restaurants"
    paginate_by         = 15

    _OPEN     = PublicRestaurantData.STATUS_OPEN
    _MAX_PAGE = 500          # OFFSET 상한 = 500 * 20 = 10,000행

    # ── GET 요청 — 최대 페이지 검사 ──────────────────────────

    def get(self, request, *args, **kwargs):
        try:
            if int(request.GET.get("page", 1)) > self._MAX_PAGE:
                raise Http404(f"페이지는 최대 {self._MAX_PAGE}까지 허용됩니다.")
        except (TypeError, ValueError):
            pass
        return super().get(request, *args, **kwargs)

    # ── 쿼리셋 ────────────────────────────────────────────────

    def get_queryset(self):
        bm_sq = (
            Bookmark.objects
            .filter(restaurant_id=OuterRef("pk"))
            .order_by()
            .values("restaurant_id")
            .annotate(n=Count("pk"))
            .values("n")
        )
        qs = (
            PublicRestaurantData.objects
            .filter(status_code=self._OPEN)
            .defer("management_no", "area", "last_modified_at",
                   "sanitation_business_type", "created_at")
            .annotate(
                bookmark_count=Coalesce(
                    Subquery(bm_sq, output_field=IntegerField()), 0
                )
            )
        )
        return _apply_restaurant_filters(
            qs, self.request.GET, include_category=True
        ).order_by("-synced_at")

    # ── 페이지네이터 — COUNT 캐시 적용 ───────────────────────

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        p   = self.request.GET
        raw = f"{p.get('search','')}|{p.get('province','')}|{'_'.join(sorted(p.getlist('business_type')))}|{p.get('min_years','')}|{'_'.join(sorted(p.getlist('cert')))}|{p.get('sw_lat','')}|{p.get('ne_lat','')}"
        key = "rl_cnt_" + hashlib.md5(raw.encode()).hexdigest()[:12]
        return CachedPaginator(
            queryset, per_page,
            cache_key=key,          # cache_ttl 기본값(300초)은 pagination.py에서 관리
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )

    # ── 컨텍스트 ──────────────────────────────────────────────

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)

        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["query_string"] = params.urlencode()

        ctx["total_count"]   = ctx["paginator"].count
        ctx["kakao_map_key"] = settings.KAKAO_MAP_API_KEY

        # 현재 페이지 식당 좌표 → JSON
        # 전국 데이터는 sync 시점에 WGS84로 변환 저장되므로 변환 없이 그대로 사용
        geo = []
        for r in ctx["object_list"]:
            if r.latitude and r.longitude:
                geo.append({"pk": r.pk, "name": r.name,
                             "lat": round(r.latitude, 6), "lng": round(r.longitude, 6)})
        raw = json.dumps(geo, ensure_ascii=False)
        # <>&를 유니코드 이스케이프로 변환 → |safe 사용해도 XSS 안전
        ctx["geo_data_json"] = (
            raw.replace("&", "\\u0026")
               .replace("<", "\\u003c")
               .replace(">", "\\u003e")
        )

        # 로그인 사용자의 북마크 PK 목록 → JS에서 하트 마커 표시에 사용
        if self.request.user.is_authenticated:
            bm_pks = list(
                Bookmark.objects
                .filter(user=self.request.user)
                .values_list("restaurant_id", flat=True)
            )
        else:
            bm_pks = []
        ctx["bookmarked_pks_json"] = json.dumps(bm_pks)

        # 전체 page_range 대신 스마트 범위만 전달 (_MAX_PAGE 초과 링크 생성 방지)
        ctx["paginator_pages"] = page_range(
            ctx["paginator"], ctx["page_obj"].number, max_page=self._MAX_PAGE
        )

        return ctx


class RestaurantDetailView(DetailView):
    """
    GET /restaurants/<pk>/
    Query params: ?sort=latest|score_high|score_low
    """

    template_name       = "honest_restaurant/restaurant_detail.html"
    context_object_name = "restaurant"

    _SORT_MAP = {
        "latest"    : "-created_at",
        "score_high": "-user_score",
        "score_low" : "user_score",
    }

    def get_queryset(self):
        return PublicRestaurantData.objects.prefetch_related("media", "bookmarks")

    def get_context_data(self, **kwargs):
        ctx        = super().get_context_data(**kwargs)
        restaurant = self.object
        user       = self.request.user

        # ── 리뷰 목록 (정렬 + 사용자 별점 annotate) ──────────
        sort     = self.request.GET.get("sort", "latest")
        ordering = self._SORT_MAP.get(sort, "-created_at")

        user_score_sq = Subquery(
            Rating.objects
            .filter(restaurant=restaurant, user=OuterRef("user"))
            .values("score")[:1]
        )
        reviews = (
            restaurant.interaction_reviews
            .select_related("user")
            .annotate(user_score=user_score_sq)
            .order_by(ordering)
        )

        # ── 영수증 인증 여부 ────────────────────────────────
        has_verified = (
            user.is_authenticated
            and ReceiptVerification.objects.filter(
                restaurant=restaurant,
                user=user,
                status__in=[
                    ReceiptVerification.STATUS_APPROVED,
                    ReceiptVerification.STATUS_PENDING,
                ],
            ).exists()
        )

        # 영수증 인증 승인 건수
        verification_count = ReceiptVerification.objects.filter(
            restaurant=restaurant,
            status=ReceiptVerification.STATUS_APPROVED,
        ).count()

        # 관리 매장 등록 여부 (관리자용)
        is_managed = False
        if user.is_staff:
            is_managed = hasattr(restaurant, 'managed')

        ctx.update({
            "reviews"            : reviews,
            "has_verified"       : has_verified,
            "can_write"          : has_verified,
            "sort"               : sort,
            "verification_count" : verification_count,
            "my_review"   : (
                Review.objects.filter(user=user, restaurant=restaurant).first()
                if user.is_authenticated else None
            ),
            "is_bookmarked": (
                Bookmark.objects.filter(user=user, restaurant=restaurant).exists()
                if user.is_authenticated else False
            ),
            "is_managed": is_managed,
        })
        return ctx


# ══════════════════════════════════════════════════════════════
# 구/군 목록 API
# ══════════════════════════════════════════════════════════════

class DistrictListView(View):
    """
    GET /restaurants/districts/?province=서울특별시
    해당 시/도에 속한 구/군 목록을 JSON으로 반환.
    """
    def get(self, request):
        province = request.GET.get("province", "").strip()
        if not province:
            return JsonResponse({"districts": []})

        addrs = (
            PublicRestaurantData.objects
            .filter(
                Q(address_road__startswith=province) |
                Q(address_jibun__startswith=province),
                status_code=PublicRestaurantData.STATUS_OPEN,
            )
            .values_list("address_road", "address_jibun")
        )

        districts = set()
        for road, jibun in addrs:
            for addr in (road, jibun):
                if addr and addr.startswith(province):
                    parts = addr.split()
                    if len(parts) >= 2:
                        districts.add(parts[1])

        return JsonResponse({"districts": sorted(districts)})


# ══════════════════════════════════════════════════════════════
# 공통 Mixin — Ajax 로그인 필요 뷰
# ══════════════════════════════════════════════════════════════

class MapMarkersView(View):
    """
    GET /restaurants/map-markers/
    지도 뷰포트 내 식당 좌표를 JSON으로 반환 (최대 1000개)
    """
    _OPEN        = PublicRestaurantData.STATUS_OPEN
    _MAX_MARKERS = 1000

    def get(self, request):
        qs = (
            PublicRestaurantData.objects
            .filter(status_code=self._OPEN)
            .only("pk", "name", "latitude", "longitude")
        )
        qs = _apply_restaurant_filters(qs, request.GET)

        markers = [
            {"pk": r.pk, "name": r.name,
             "lat": round(r.latitude, 6), "lng": round(r.longitude, 6)}
            for r in qs.order_by("-synced_at")[:self._MAX_MARKERS]
            if r.latitude and r.longitude
        ]
        return JsonResponse({"markers": markers})


class AjaxLoginRequiredMixin(LoginRequiredMixin):
    """
    LoginRequiredMixin 확장:
    - login_url 기본값 "login" 설정
    - Ajax 요청에서 로그인 필요 시 JSON 401 반환 (리다이렉트 대신)
    """
    login_url = "login"

    @staticmethod
    def _is_ajax(request):
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def handle_no_permission(self):
        if self._is_ajax(self.request):
            return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
        return super().handle_no_permission()


# ══════════════════════════════════════════════════════════════
# Receipt Verification Views
# ══════════════════════════════════════════════════════════════

class ReceiptVerifyView(AjaxLoginRequiredMixin, View):
    """
    GET  /restaurants/<pk>/verify/ — 업로드 폼 렌더링
    POST /restaurants/<pk>/verify/ — 영수증 제출 (HTML 또는 Axios)
    """

    def _restaurant(self):
        return get_object_or_404(PublicRestaurantData, pk=self.kwargs["pk"])

    def _existing(self, restaurant):
        return ReceiptVerification.objects.filter(
            restaurant=restaurant, user=self.request.user
        ).first()

    def _render_form(self, request, restaurant, form):
        return render(request, "honest_restaurant/restaurant_verify.html", {
            "restaurant": restaurant,
            "form"      : form,
            "existing"  : self._existing(restaurant),
        })

    def get(self, request, pk):
        return self._render_form(request, self._restaurant(), ReceiptVerificationForm())

    def post(self, request, pk):
        restaurant = self._restaurant()
        form       = ReceiptVerificationForm(request.POST, request.FILES)

        if not form.is_valid():
            if self._is_ajax(request):
                errors = {f: e.as_text() for f, e in form.errors.items()}
                return JsonResponse({"errors": errors}, status=400)
            return self._render_form(request, restaurant, form)

        # 기존 인증이 있으면 업데이트, 없으면 신규 생성
        ReceiptVerification.objects.update_or_create(
            restaurant=restaurant,
            user=request.user,
            defaults={
                "receipt_image": form.cleaned_data["receipt_image"],
                "comment"      : form.cleaned_data.get("comment", ""),
                "status"       : ReceiptVerification.STATUS_APPROVED,
            },
        )

        redirect_url = (
            reverse("public_restaurants:restaurant-detail-page", kwargs={"pk": pk})
            + "#review-section"
        )
        if self._is_ajax(request):
            return JsonResponse({"success": True, "redirect": redirect_url})
        return redirect(redirect_url)


class VerifyCancelView(View):
    """
    POST /restaurants/<pk>/verify/cancel/
    navigator.sendBeacon 호출 — 리뷰 미작성 상태이면 영수증 인증 삭제.
    """

    def post(self, request, pk):
        if request.user.is_authenticated:
            has_review = Review.objects.filter(
                restaurant_id=pk, user=request.user
            ).exists()
            if not has_review:
                ReceiptVerification.objects.filter(
                    restaurant_id=pk, user=request.user
                ).delete()
        return HttpResponse(status=204)


# ══════════════════════════════════════════════════════════════
# Media Views
# ══════════════════════════════════════════════════════════════

class MediaUploadView(AjaxLoginRequiredMixin, View):
    """POST /restaurants/<pk>/media/upload/"""

    _VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm"}

    def post(self, request, pk):
        restaurant = get_object_or_404(PublicRestaurantData, pk=pk)
        form       = RestaurantMediaForm(request.POST, request.FILES)

        if not form.is_valid():
            if self._is_ajax(request):
                return JsonResponse({"errors": form.errors}, status=400)
            return redirect("public_restaurants:restaurant-detail-page", pk=pk)

        uploaded_file = form.cleaned_data["file"]
        ext           = os.path.splitext(uploaded_file.name)[1].lower()
        media_type    = (
            RestaurantMedia.TYPE_VIDEO
            if ext in self._VIDEO_EXTS
            else RestaurantMedia.TYPE_IMAGE
        )
        RestaurantMedia.objects.create(
            restaurant  = restaurant,
            uploaded_by = request.user,
            file        = uploaded_file,
            media_type  = media_type,
        )

        if self._is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("public_restaurants:restaurant-detail-page", pk=pk)


class MediaDeleteView(AjaxLoginRequiredMixin, View):
    """POST /restaurants/<pk>/media/<media_pk>/delete/"""

    def post(self, request, pk, media_pk):
        media = get_object_or_404(RestaurantMedia, pk=media_pk, restaurant__pk=pk)

        if media.uploaded_by == request.user or request.user.is_staff:
            if media.file and os.path.isfile(media.file.path):
                os.remove(media.file.path)
            media.delete()

        if self._is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("public_restaurants:restaurant-detail-page", pk=pk)

