"""
honest_restaurant.views
=======================
레이어 구분
    RestaurantViewSet          — DRF ReadOnly JSON API
    IndexView                  — 메인 페이지 (TemplateView)
    RestaurantListView         — 목록 페이지 (ListView)
    RestaurantDetailView       — 상세 페이지 (DetailView)
    ─────────────────────────────────────────────
    ReceiptVerifyView          — 영수증 업로드 (LoginRequiredMixin + View)
    VerifyCancelView           — 이탈 시 인증 취소 beacon 처리 (View)
    MediaUploadView            — 미디어 업로드 (LoginRequiredMixin + View)
    MediaDeleteView            — 미디어 삭제  (LoginRequiredMixin + View)
    SeoulRestaurantSyncer      — 서울시 공공 API 동기화 클래스

페이지네이션 관련 클래스·함수는 pagination.py 에서 관리한다.
"""

import hashlib
import json

from pyproj import Transformer as _GeoTransformer
_TM_TO_WGS84  = _GeoTransformer.from_crs('EPSG:5174', 'EPSG:4326', always_xy=True)
_WGS84_TO_TM  = _GeoTransformer.from_crs('EPSG:4326', 'EPSG:5174', always_xy=True)
import logging
import os
from datetime import datetime, timedelta

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

class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    서울시 공공 식당 데이터 Read-only API

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
    filterset_fields = ["province", "district", "business_type", "sanitation_business_type"]
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
        from django.shortcuts import redirect
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
        p             = self.request.GET
        search        = p.get("search",        "").strip()
        province      = p.get("province",      "").strip()
        business_type = p.get("business_type", "").strip()
        sw_lat        = p.get("sw_lat",        "").strip()
        sw_lng        = p.get("sw_lng",        "").strip()
        ne_lat        = p.get("ne_lat",        "").strip()
        ne_lng        = p.get("ne_lng",        "").strip()

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
            .defer(
                "management_no",
                "area", "last_modified_at", "sanitation_business_type",
                "created_at",
            )
            .annotate(
                bookmark_count=Coalesce(
                    Subquery(bm_sq, output_field=IntegerField()), 0
                )
            )
        )

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(address_road__icontains=search)
                | Q(address_jibun__icontains=search)
                | Q(category_name__icontains=search)
                | Q(province__icontains=search)
                | Q(district__icontains=search)
                | Q(business_type__icontains=search)
            )
        if province:
            qs = qs.filter(province=province)
        if business_type:
            qs = qs.filter(business_type=business_type)

        # 지도 범위 필터 (DB가 WGS84 저장 → 변환 없이 직접 비교)
        if all([sw_lat, sw_lng, ne_lat, ne_lng]):
            try:
                qs = qs.filter(
                    longitude__gte=float(sw_lng), longitude__lte=float(ne_lng),
                    latitude__gte=float(sw_lat),  latitude__lte=float(ne_lat),
                )
            except (ValueError, TypeError):
                pass

        return qs.order_by("-synced_at")

    # ── 페이지네이터 — COUNT 캐시 적용 ───────────────────────

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        p   = self.request.GET
        raw = f"{p.get('search','')}|{p.get('province','')}|{p.get('business_type','')}|{p.get('sw_lat','')}|{p.get('ne_lat','')}"
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
        base = PublicRestaurantData.objects.filter(status_code=self._OPEN)

        ctx["province_choices"] = (
            base.exclude(province="")
            .values_list("province", flat=True)
            .distinct().order_by("province")
        )
        ctx["business_type_choices"] = (
            base.exclude(business_type="")
            .values_list("business_type", flat=True)
            .distinct().order_by("business_type")
        )

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

    model               = PublicRestaurantData
    template_name       = "honest_restaurant/restaurant_detail.html"
    context_object_name = "restaurant"

    _SORT_MAP = {
        "latest"    : "-created_at",
        "score_high": "-user_score",
        "score_low" : "user_score",
    }

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

        # 관리 매장 등록 여부 (관리자용)
        is_managed = False
        if user.is_staff:
            is_managed = hasattr(restaurant, 'managed')

        ctx.update({
            "reviews"     : reviews,
            "has_verified": has_verified,
            "can_write"   : has_verified,
            "sort"        : sort,
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
# 공통 Mixin — Ajax 로그인 필요 뷰
# ══════════════════════════════════════════════════════════════

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
                "status"       : ReceiptVerification.STATUS_PENDING,
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


# ══════════════════════════════════════════════════════════════
# 서울시 공공 API 동기화 클래스
# — management command `sync_seoul_restaurants` 에서 사용
# ══════════════════════════════════════════════════════════════

class SeoulRestaurantSyncer:
    """
    서울 열린데이터광장 음식점 인허가 데이터를 가져와 DB에 저장하는 클래스.

    사용 예)
        syncer = SeoulRestaurantSyncer("일반음식점")
        rows   = syncer.fetch(1, 1000)
        syncer.save(rows)
    """

    # ── 클래스 상수 ─────────────────────────────────────────
    API_BASE     = "http://openapi.seoul.go.kr:8088"
    BATCH_SIZE   = 1000
    SUCCESS_CODE = "INFO-000"

    SERVICE_MAP = {
        "일반음식점": "LOCALDATA_072404",
        "휴게음식점": "LOCALDATA_072405",
    }

    DISTRICTS = [
        "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
        "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구",
        "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구",
        "강동구",
    ]

    _log = logging.getLogger(__name__)

    # ── 초기화 ──────────────────────────────────────────────

    def __init__(self, restaurant_type="일반음식점"):
        self.restaurant_type = restaurant_type

    # ── 공개 메서드 ─────────────────────────────────────────

    def fetch(self, start, end):
        """
        API에서 start~end 번째 행을 가져온다.
        실패하면 빈 리스트를 반환한다.
        """
        service = self.SERVICE_MAP[self.restaurant_type]
        url     = (
            f"{self.API_BASE}/{settings.SEOUL_API_KEY}"
            f"/json/{service}/{start}/{end}/"
        )
        self._log.info("[SeoulAPI:%s] 호출 %s~%s", self.restaurant_type, start, end)

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            self._log.error("[SeoulAPI:%s] 타임아웃", self.restaurant_type)
            return []
        except requests.exceptions.RequestException as exc:
            self._log.error("[SeoulAPI:%s] 요청 실패: %s", self.restaurant_type, exc)
            return []
        except ValueError:
            self._log.error("[SeoulAPI:%s] JSON 파싱 실패", self.restaurant_type)
            return []

        service_data = data.get(service, {})
        code         = service_data.get("RESULT", {}).get("CODE", "")
        if code != self.SUCCESS_CODE:
            self._log.warning("[SeoulAPI:%s] 응답 코드: %s", self.restaurant_type, code)
            return []

        rows = service_data.get("row", [])
        self._log.info("[SeoulAPI:%s] %d건 수신", self.restaurant_type, len(rows))
        return rows

    def save(self, rows):
        """
        rows를 파싱해 DB에 upsert 저장한다.
        Returns: (created_count, updated_count)
        """
        created = updated = skipped = 0

        for row in rows:
            mgt_no = row.get("MGTNO", "").strip()
            if not mgt_no:
                skipped += 1
                continue
            if row.get("TRDSTATEGBN", "").strip() != "01":  # 영업중만 저장
                skipped += 1
                continue

            name = row.get("BPLCNM", "").strip()
            if row.get("UPTAENM", "").strip() == "편의점" or "편의점" in name:
                skipped += 1
                continue

            defaults = self._build_defaults(row)

            if self._is_duplicate(defaults, mgt_no):
                skipped += 1
                continue

            try:
                _, is_new = PublicRestaurantData.objects.update_or_create(
                    management_no=mgt_no, defaults=defaults
                )
                created += is_new
                updated += not is_new
            except Exception as exc:
                self._log.error("[SeoulAPI] DB 저장 실패 MGTNO=%s: %s", mgt_no, exc)

        self._log.info(
            "[SeoulAPI] 완료 — 신규:%d / 갱신:%d / 스킵:%d", created, updated, skipped
        )
        return created, updated

    # ── 내부 헬퍼 ───────────────────────────────────────────

    def _build_defaults(self, row):
        """API 응답 행 1건 → 모델 defaults dict"""
        road  = row.get("RDNWHLADDR", "").strip()
        jibun = row.get("SITEWHLADDR", "").strip()
        addr  = road or jibun
        return {
            "name"                    : row.get("BPLCNM",       "").strip(),
            "address_road"            : road,
            "address_jibun"           : jibun,
            "province"                : addr.split()[0] if addr else "",
            "district"                : self._extract_district(road) or self._extract_district(jibun),
            "phone"                   : row.get("SITETEL",      "").strip(),
            "business_type"           : row.get("UPTAENM",      "").strip(),
            "category_name"           : row.get("DTLSTATENM",   "").strip(),
            "sanitation_business_type": row.get("SANITTNBIZNM", "").strip(),
            "license_date"            : self._parse_date(row.get("APVPERMYMD")),
            "status_code"             : row.get("TRDSTATEGBN",  "").strip(),
            "area"                    : self._parse_float(row.get("SITEAREA")),
            "last_modified_at"        : self._parse_datetime(row.get("LASTMODTS")),
            "longitude"               : self._parse_float(row.get("X")),
            "latitude"                : self._parse_float(row.get("Y")),
        }

    def _is_duplicate(self, defaults, mgt_no):
        """같은 상호+주소+업태가 이미 다른 관리번호로 존재하면 True"""
        field = "address_road" if defaults.get("address_road") else "address_jibun"
        val   = defaults.get(field, "")
        if not val:
            return False
        return PublicRestaurantData.objects.filter(
            name=defaults["name"],
            business_type=defaults["business_type"],
            **{field: val},
        ).exclude(management_no=mgt_no).exists()

    def _extract_district(self, address):
        if not address:
            return ""
        for d in self.DISTRICTS:
            if d in address:
                return d
        return ""

    @staticmethod
    def _parse_date(val):
        if not val or not val.strip():
            return None
        try:
            return datetime.strptime(val.strip(), "%Y%m%d").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(val):
        if not val or not val.strip():
            return None
        try:
            return datetime.strptime(val.strip()[:14], "%Y%m%d%H%M%S")
        except ValueError:
            return None

    @staticmethod
    def _parse_float(val):
        if not val or not val.strip():
            return None
        try:
            return float(val.strip())
        except ValueError:
            return None


# ══════════════════════════════════════════════════════════════
# 전국 공공 API 동기화 클래스
# — management command `sync_national_restaurants` 에서 사용
# ══════════════════════════════════════════════════════════════

class NationalRestaurantSyncer:
    """
    공공데이터포털 행정안전부_식품_일반음식점 API 동기화.

    API 명세: https://www.data.go.kr/data/15154916/openapi.do
    - pageNo + numOfRows 페이지네이션 (max: 100)
    - returnType: json
    - 응답 필드: LCPMT_YMD, SALS_STTS_CD, BPLC_NM, ROAD_NM_ADDR 등

    사용 예)
        syncer = NationalRestaurantSyncer()
        rows   = syncer.fetch(1)
        syncer.save(rows)
    """

    BATCH_SIZE = 100  # API max: 100
    SUCCESS_CODE = "00"
    RETURN_TYPE = "json"

    _log = logging.getLogger(__name__)

    def __init__(self):
        self.api_key = os.getenv("NATIONAL_API_KEY", "")
        self.api_url = settings.NATIONAL_API_URL

        if not self.api_key:
            raise ValueError("NATIONAL_API_KEY 환경변수가 설정되지 않았습니다")
        if not self.api_url:
            raise ValueError("NATIONAL_API_URL이 settings.py에 설정되지 않았습니다")

    def fetch(self, page_no):
        """
        API에서 page_no 페이지의 데이터를 가져온다.
        - pageNo: 페이지 번호 (1부터 시작)
        - numOfRows: 한 페이지 행 수 (최대 100)
        실패하면 빈 리스트를 반환한다.
        """
        params = {
            "serviceKey": self.api_key,
            "pageNo": page_no,
            "numOfRows": self.BATCH_SIZE,
            "returnType": self.RETURN_TYPE,
            "cond[SALS_STTS_CD::EQ]": "01",  # 영업 중인 가게만
        }

        self._log.info(
            "[NationalAPI] 페이지 %d 호출 (numOfRows=%d)",
            page_no, self.BATCH_SIZE
        )

        # 네트워크 오류 시 최대 3회 재시도
        for attempt in range(1, 4):
            try:
                resp = requests.get(self.api_url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.exceptions.Timeout:
                self._log.warning("[NationalAPI] 타임아웃 (시도 %d/3)", attempt)
                if attempt == 3:
                    return []
            except requests.exceptions.RequestException as exc:
                self._log.warning("[NationalAPI] 요청 실패 (시도 %d/3): %s", attempt, exc)
                if attempt == 3:
                    return []
            except ValueError:
                self._log.error("[NationalAPI] JSON 파싱 실패")
                return []

        # 응답 구조: response → body → items → item (배열)
        if "response" not in data:
            self._log.warning("[NationalAPI] 'response' 키 없음")
            return []

        resp_data = data.get("response", {})
        header = resp_data.get("header", {})
        code = str(header.get("resultCode", ""))  # "0" 또는 "00"

        # resultCode 정규화: "0", "00" 모두 성공
        if code not in ["0", "00"]:
            msg = header.get("resultMsg", "Unknown error")
            self._log.warning("[NationalAPI] 응답 코드: %s (%s)", code, msg)
            return []

        body = resp_data.get("body", {})
        items_obj = body.get("items", {})

        # items가 dict인 경우: items.item (배열)
        # items가 list인 경우: items (배열) - 호환성
        if isinstance(items_obj, dict):
            items = items_obj.get("item", [])
        else:
            items = items_obj if isinstance(items_obj, list) else []

        self._log.info("[NationalAPI] %d건 수신", len(items))
        return items

    def save(self, rows):
        """
        rows를 파싱해 DB에 upsert 저장한다.
        Returns: (created_count, updated_count)
        """
        created = updated = skipped = 0

        for row in rows:
            # 관리번호 필수
            mgt_no = row.get("MNG_NO", "").strip()
            if not mgt_no:
                skipped += 1
                continue

            # 상호명 필수
            name = row.get("BPLC_NM", "").strip()
            if not name:
                skipped += 1
                continue

            # 영업 중인 것만 저장 (SALS_STTS_CD: 01=영업, 02=휴업, 03=폐업)
            status_code = row.get("SALS_STTS_CD", "").strip()
            if status_code != "01":
                skipped += 1
                continue

            # 편의점 제외
            biz_type = row.get("BZSTAT_SE_NM", "").strip()
            if "편의점" in name or "편의점" in biz_type:
                skipped += 1
                continue

            defaults = self._build_defaults(row)

            try:
                _, is_new = PublicRestaurantData.objects.update_or_create(
                    management_no=mgt_no, defaults=defaults
                )
                created += is_new
                updated += not is_new
            except Exception as exc:
                self._log.error("[NationalAPI] DB 저장 실패 MNG_NO=%s: %s", mgt_no, exc)
                skipped += 1

        self._log.info(
            "[NationalAPI] 페이지 완료 — 신규:%d / 갱신:%d / 스킵:%d",
            created, updated, skipped
        )
        return created, updated

    # ── 내부 헬퍼 ───────────────────────────────────────────

    def _build_defaults(self, row):
        """
        National API 응답 행 1건 → 모델 defaults dict

        API 필드명 (실제):
          BPLC_NM: 사업장명
          ROAD_NM_ADDR: 도로명주소
          LOTNO_ADDR: 지번주소
          OPN_ATMY_GRP_CD: 개방자치단체코드 (시도/시군구 추출 필요)
          TELNO: 전화번호
          BZSTAT_SE_NM: 업태명 (예: 경양식)
          SNTTN_BZSTAT_NM: 위생업태명
          LCPMT_YMD: 인허가일자 (YYYY-MM-DD)
          SALS_STTS_CD: 영업상태코드 (01=영업, 02=휴업, 03=폐업)
          FCLT_TOTAL_SCL: 시설총면적 (㎡)
          DAT_UPDT_PNT: 데이터갱신시점 (YYYY-MM-DD HH:MM:SS)
          CRD_INFO_X: X좌표 (TM좌표, WGS84로 변환 필요)
          CRD_INFO_Y: Y좌표 (TM좌표, WGS84로 변환 필요)
          MNG_NO: 관리번호
        """
        road = row.get("ROAD_NM_ADDR", "").strip()
        jibun = row.get("LOTNO_ADDR", "").strip()
        addr = road or jibun

        # OPN_ATMY_GRP_CD에서 시도/시군구 추출
        # 예: "3990000" → 첫 2자리: 시도, 다음 3자리: 시군구
        opn_code = row.get("OPN_ATMY_GRP_CD", "").strip()
        province = ""
        district = ""
        if opn_code and len(opn_code) >= 5:
            # 첫 2자리로 시도 판정 (서울=1100, 부산=2600, 경기=3100 등)
            prov_code = opn_code[:2]
            prov_map = {
                "11": "서울특별시", "26": "부산광역시", "27": "대구광역시",
                "28": "인천광역시", "29": "광주광역시", "30": "대전광역시",
                "31": "울산광역시", "41": "경기도", "42": "강원도",
                "43": "충청북도", "44": "충청남도", "45": "전라북도",
                "46": "전라남도", "47": "경상북도", "48": "경상남도",
                "49": "제주도",
            }
            province = prov_map.get(prov_code, "")

        # 주소가 없으면 첫 번째 토큰에서 추출
        if not province and addr:
            province = addr.split()[0] if addr else ""

        return {
            "name": row.get("BPLC_NM", "").strip(),
            "address_road": road,
            "address_jibun": jibun,
            "province": province,
            "district": district,
            "phone": row.get("TELNO", "").strip(),
            "business_type": row.get("BZSTAT_SE_NM", "").strip(),
            "category_name": "",  # API에서 제공하지 않음
            "sanitation_business_type": row.get("SNTTN_BZSTAT_NM", "").strip(),
            "license_date": self._parse_date_iso(row.get("LCPMT_YMD")),
            "status_code": row.get("SALS_STTS_CD", "").strip(),
            "area": self._parse_float(row.get("FCLT_TOTAL_SCL")),
            "last_modified_at": self._parse_datetime_iso(row.get("DAT_UPDT_PNT")),
            "latitude": self._convert_tm_to_wgs84_lat(
                row.get("CRD_INFO_X"), row.get("CRD_INFO_Y")
            ),
            "longitude": self._convert_tm_to_wgs84_lng(
                row.get("CRD_INFO_X"), row.get("CRD_INFO_Y")
            ),
        }

    @staticmethod
    def _parse_date_iso(val):
        """YYYY-MM-DD 형식 → date 객체 (ISO 형식)"""
        if not val or not val.strip():
            return None
        try:
            return datetime.strptime(val.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime_iso(val):
        """YYYY-MM-DD HH:MM:SS 형식 → datetime 객체 (ISO 형식)"""
        if not val or not val.strip():
            return None
        try:
            return datetime.strptime(val.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    @staticmethod
    def _parse_float(val):
        """숫자 문자열 → float 또는 None"""
        if not val or not val.strip():
            return None
        try:
            return float(val.strip())
        except ValueError:
            return None

    @staticmethod
    def _convert_tm_to_wgs84_lat(x_str, y_str):
        """
        중부원점TM 좌표 (EPSG:5174) → WGS84 위도 (EPSG:4326)

        API에서 제공하는 CRD_INFO_X, CRD_INFO_Y는 TM좌표이므로
        기존의 _TM_TO_WGS84 변환기 사용
        """
        try:
            x = float(x_str) if x_str else None
            y = float(y_str) if y_str else None
            if x is None or y is None:
                return None
            lng, lat = _TM_TO_WGS84.transform(x, y)
            return lat
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _convert_tm_to_wgs84_lng(x_str, y_str):
        """
        중부원점TM 좌표 (EPSG:5174) → WGS84 경도 (EPSG:4326)
        """
        try:
            x = float(x_str) if x_str else None
            y = float(y_str) if y_str else None
            if x is None or y is None:
                return None
            lng, lat = _TM_TO_WGS84.transform(x, y)
            return lng
        except (ValueError, TypeError):
            return None
