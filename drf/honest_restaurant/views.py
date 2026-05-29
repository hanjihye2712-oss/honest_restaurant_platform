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
import random
from datetime import date, timedelta

import requests
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, IntegerField, Max, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape, mark_safe
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import filters, viewsets
from django_filters.rest_framework import DjangoFilterBackend

from .forms import MenuItemForm, ReceiptVerificationForm, RestaurantInfoForm, RestaurantMediaForm
from .models import PublicRestaurantData, ReceiptVerification, RestaurantMedia, RestaurantMenuItem, RestaurantOwnerApplication
from .services import verify_business_number
from .pagination import CachedPaginator, RestaurantCursorPagination, page_range
from .serializers import (
    PublicRestaurantDataDetailSerializer,
    PublicRestaurantDataSerializer,
)
from interactions.models import Bookmark, Rating, Review


# ══════════════════════════════════════════════════════════════
# 신뢰 점수 공통 헬퍼 — _list_trust_level / _calc_level_score 공유
# ══════════════════════════════════════════════════════════════

LOGIN_URL = "/accounts/login/"

# ── 메인 페이지 캐시 설정 ─────────────────────────────────────
# tasks.py warm_index_cache가 50분 주기로 갱신 → cold-start 제거
# Celery가 중단돼도 TTL(1시간) 동안은 기존 캐시가 서빙됨
_INDEX_CACHE_KEY = 'index_sections'
_INDEX_CACHE_TTL = 60 * 60  # 1시간

# 레벨 판정 임계값 (총점 기준)
_LEVEL_MIN_SCORE = {1: 90, 2: 75, 3: 55}

# (임계값, 점수) 순으로 높은 것부터 배치
_VISIT_SCORE_TABLE   = [(1000, 15), (500, 12), (200, 10), (50, 8), (10, 6)]
_HISTORY_SCORE_TABLE = [(50, 20), (30, 15), (20, 13), (10, 10), (5, 5), (3, 3), (1, 1)]


def _lookup_score(value: float, table: list) -> int:
    """(임계값, 점수) 테이블에서 value에 해당하는 점수를 반환한다."""
    for threshold, score in table:
        if value >= threshold:
            return score
    return 0


def _calc_cert_count(r) -> int:
    """정부인증 개수 (0~4)."""
    return sum([
        bool(r.hygiene_grade_valid),
        bool(r.is_excellent_restaurant),
        bool(r.is_ansim_restaurant),
        bool(r.is_goodprice_shop),
    ])


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
        if request.GET.get('owner') == '1':
            return redirect('public_restaurants:owner-dashboard')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            unnotified = RestaurantOwnerApplication.objects.filter(
                user=self.request.user,
                status=RestaurantOwnerApplication.STATUS_APPROVED,
                approval_notified=False,
            ).first()
            if unnotified:
                unnotified.approval_notified = True
                unnotified.save(update_fields=["approval_notified"])
                ctx["show_approval_alert"] = True
        ctx["sections"] = cache.get_or_set(_INDEX_CACHE_KEY, _build_index_sections, _INDEX_CACHE_TTL)
        return ctx


def _build_index_sections():
    """
    메인 페이지 8개 섹션 데이터 — 각 섹션 최대 4개 식당.

    주간 로테이션: 각 섹션에서 후보 12개를 뽑아두고, 이번 주 번호로
    어떤 4개를 보여줄지 결정한다. 주마다 다른 가게가 노출되어
    재방문 유저도 새로운 가게를 발견할 수 있다.
    (주 1 → 후보 0~3번, 주 2 → 후보 4~7번, 주 3 → 후보 8~11번, 반복)
    """
    today       = date.today()
    now         = timezone.now()
    thirty_ago  = now - timedelta(days=30)
    sixty_ago   = now - timedelta(days=60)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    twenty_yrs  = today.replace(year=today.year - 20)
    one_yr      = today.replace(year=today.year - 1)

    # 주간 로테이션 시드 (ISO 주 번호, 1~53)
    # 월별로 바꾸려면: week_seed = now.month
    week_seed = now.isocalendar()[1]

    POOL = 12   # 후보 수 (주당 4개 × 3주 사이클)
    SHOW = 4    # 노출 수

    def _rotate(items):
        """후보 리스트에서 이번 주에 보여줄 SHOW개를 선택한다."""
        n = len(items)
        if n <= SHOW:
            return items
        start = (week_seed * SHOW) % n
        end   = start + SHOW
        # 끝에서 잘리면 앞에서 이어붙임
        return (items + items)[start:end]

    open_qs = PublicRestaurantData.objects.filter(status_code=PublicRestaurantData.STATUS_OPEN)

    _STATIC = '/static/img/honest_restaurant/'
    _IMG_MAP = [
        ('김밥',      _STATIC + 'gimbap.jpg'),
        ('칼국수',    _STATIC + 'kalguksu.jpg'),
        ('국수',      _STATIC + 'kalguksu.jpg'),
        ('냉면',      _STATIC + 'naengmyeon.jpg'),
        ('비빔',      _STATIC + 'bibimbap.jpg'),
        ('백반',      _STATIC + 'bibimbap.jpg'),
        ('한식',      _STATIC + 'bibimbap.jpg'),
        ('분식',      _STATIC + 'tteokbokki.jpg'),
        ('떡볶이',    _STATIC + 'tteokbokki.jpg'),
        ('패스트푸드', _STATIC + 'tteokbokki.jpg'),
        ('키즈카페',  _STATIC + 'tteokbokki.jpg'),
        ('전통찻집',  _STATIC + 'tteok.jpg'),
        ('라이브카페', _STATIC + 'tteok.jpg'),
        ('까페',      _STATIC + 'tteok.jpg'),
        ('카페',      _STATIC + 'tteok.jpg'),
        ('커피',      _STATIC + 'tteok.jpg'),
        ('국밥',      _STATIC + 'gukbap.jpg'),
        ('중국',      _STATIC + 'gukbap.jpg'),
        ('순대',      _STATIC + 'sundae.jpg'),
        ('탕류',      _STATIC + 'haejangguk.jpg'),
        ('해장',      _STATIC + 'haejangguk.jpg'),
        ('식육',      _STATIC + 'naengmyeon_grilled.jpg'),
        ('숯불',      _STATIC + 'naengmyeon_grilled.jpg'),
        ('통닭',      _STATIC + 'naengmyeon_grilled.jpg'),
        ('치킨',      _STATIC + 'naengmyeon_grilled.jpg'),
        ('호프',      _STATIC + 'naengmyeon_grilled.jpg'),
        ('횟집',      _STATIC + 'sundae.jpg'),
        ('생선',      _STATIC + 'pajeon.jpg'),
        ('소주방',    _STATIC + 'pajeon.jpg'),
        ('정종',      _STATIC + 'pajeon.jpg'),
        ('감성주점',  _STATIC + 'pajeon.jpg'),
        ('외국음식',  _STATIC + 'doenjang.jpg'),
        ('두부',      _STATIC + 'doenjang.jpg'),
        ('보쌈',      _STATIC + 'bossam.jpg'),
        ('경양식',    _STATIC + 'bossam.jpg'),
        ('뷔페',      _STATIC + 'hanjeongsik.jpg'),
        ('패밀리',    _STATIC + 'hanjeongsik.jpg'),
        ('한정식',    _STATIC + 'hanjeongsik.jpg'),
        ('일식',      _STATIC + 'sundubu.jpg'),
        ('복어',      _STATIC + 'sundubu.jpg'),
        ('떡',        _STATIC + 'tteok.jpg'),
    ]
    _IMG_FALLBACKS = [
        _STATIC + 'gimbap.jpg',
        _STATIC + 'kalguksu.jpg',
        _STATIC + 'bibimbap.jpg',
        _STATIC + 'tteok.jpg',
        _STATIC + 'gukbap.jpg',
        _STATIC + 'pajeon.jpg',
        _STATIC + 'naengmyeon.jpg',
        _STATIC + 'doenjang.jpg',
        _STATIC + 'bossam.jpg',
        _STATIC + 'haejangguk.jpg',
        _STATIC + 'hanjeongsik.jpg',
        _STATIC + 'tteokbokki.jpg',
        _STATIC + 'naengmyeon_grilled.jpg',
        _STATIC + 'sundae.jpg',
        _STATIC + 'sundubu.jpg',
    ]
    IMG_TOTAL = len(_IMG_FALLBACKS)

    def _img_url(business_type, pk=0, used=None):
        """업종에 맞는 이미지 URL 반환. 중복 방지."""
        bt = business_type or ''
        preferred = None
        for keyword, url in _IMG_MAP:
            if keyword in bt:
                preferred = url
                break

        if preferred and (used is None or preferred not in used):
            return preferred

        pk_base = _IMG_FALLBACKS[pk % IMG_TOTAL]
        if used is None or pk_base not in used:
            return pk_base

        for offset in range(1, IMG_TOTAL):
            candidate = _IMG_FALLBACKS[(pk + offset) % IMG_TOTAL]
            if used is None or candidate not in used:
                return candidate

        return preferred or pk_base

    def _simple_lv(r):
        cert_count = _calc_cert_count(r)
        years = r.operating_years or 0
        if cert_count >= 3 or (cert_count >= 2 and years >= 15): return 1
        if cert_count >= 2 or years >= 20: return 2
        if cert_count >= 1 or years >= 5:  return 3
        return 4

    def _card(r, foot_left='', foot_right='', rank=None, img_url=''):
        certs = []
        if r.is_excellent_restaurant: certs.append('모범음식점')
        if r.hygiene_grade_valid:     certs.append('위생등급 우수')
        if r.is_ansim_restaurant:     certs.append('안심식당')
        if r.is_goodprice_shop:       certs.append('착한가격업소')

        yrs = r.operating_years
        meta_parts = [r.business_type] if r.business_type else []
        if r.province:
            meta_parts.append(r.province)
        if yrs and yrs >= 10:
            meta_parts.append(f'{int(yrs)}년 노포')
        elif yrs:
            meta_parts.append(f'{int(yrs)}년')

        try:
            ai_p = r.ai_profile
        except Exception:
            ai_p = None

        if not foot_left and ai_p and ai_p.receipt_ocr_count > 0:
            foot_left  = f'영수증 {ai_p.receipt_ocr_count:,}건'
            foot_right = f'일치율 {round(ai_p.price_match_rate * 100)}%'

        keywords = []
        if ai_p and isinstance(ai_p.top_positive_tags, dict) and ai_p.top_positive_tags:
            keywords = [tag for tag, _ in
                        sorted(ai_p.top_positive_tags.items(), key=lambda x: x[1], reverse=True)[:3]]

        return {
            'pk':         r.pk,
            'name':       r.name,
            'certs':      ' · '.join(certs[:2]),
            'meta':       ' · '.join(meta_parts),
            'keywords':   keywords,
            'lv':         _simple_lv(r),
            'img_url':    img_url,
            'foot_left':  foot_left,
            'foot_right': foot_right,
            'rank':       rank,
        }

    def _to_cards(restaurants, foot_fn, rank_fn=None, used_imgs=None):
        """restaurants → card dict 리스트. 섹션 내 이미지 중복 방지."""
        if used_imgs is None:
            used_imgs = set()
        cards = []
        for i, r in enumerate(restaurants):
            img = _img_url(r.business_type or '', r.pk, used_imgs)
            used_imgs.add(img)
            rank = rank_fn(i) if rank_fn else None
            fl, fr = foot_fn(r)
            cards.append(_card(r, fl, fr, rank=rank, img_url=img))
        return cards, used_imgs

    def _pad(cards, used_imgs, exclude_pks, foot_fn=None):
        """SHOW개 미만이면 다양한 업종의 fallback 가게로 채운다."""
        if len(cards) >= SHOW:
            return cards
        needed = SHOW - len(cards)
        fallback = list(
            open_qs.select_related('ai_profile')
            .annotate(bm=Count('bookmarks'))
            .exclude(pk__in=list(exclude_pks))
            .order_by('business_type', 'pk')[:needed * 5]
        )
        # 이미 선택된 업종 피해 다양하게
        seen_bt = {c['meta'].split(' · ')[0] for c in cards if c['meta']}
        chosen = []
        for r in fallback:
            if len(chosen) >= needed:
                break
            if (r.business_type or '') not in seen_bt:
                chosen.append(r)
                seen_bt.add(r.business_type or '')
        # 업종 다양성 채워도 부족하면 그냥 추가
        if len(chosen) < needed:
            already = {r.pk for r in chosen}
            for r in fallback:
                if len(chosen) >= needed:
                    break
                if r.pk not in already:
                    chosen.append(r)
        for r in chosen:
            img = _img_url(r.business_type or '', r.pk, used_imgs)
            used_imgs.add(img)
            if foot_fn:
                try:
                    fl, fr = foot_fn(r)
                except Exception:
                    fl, fr = f'찜 {r.bm:,}개', ''
            else:
                fl, fr = f'찜 {r.bm:,}개', ''
            cards.append(_card(r, fl, fr, img_url=img))
        return cards

    # ── 1. 업종별 저장수 TOP ──
    biz_qs = (
        open_qs.annotate(bm=Count('bookmarks'))
        .select_related('ai_profile')
        .order_by('business_type', '-bm')
    )
    seen_biz, biz_pool = set(), []
    for r in biz_qs[:500]:
        if r.business_type and r.business_type not in seen_biz:
            seen_biz.add(r.business_type)
            biz_pool.append(r)
            if len(biz_pool) >= POOL:
                break
    biz_rotated = _rotate(biz_pool)
    biz_top, biz_imgs = _to_cards(
        biz_rotated,
        foot_fn=lambda r: (f'찜 {r.bm:,}개', ''),
        rank_fn=lambda i: i + 1,
    )
    biz_top = _pad(biz_top, biz_imgs, {r.pk for r in biz_rotated},
                   foot_fn=lambda r: (f'찜 {r.bm:,}개', ''))

    # ── 2. 노포 명예의 전당 ──
    veteran_pool = list(
        open_qs.select_related('ai_profile')
        .filter(license_date__isnull=False, license_date__lte=twenty_yrs)
        .order_by('license_date')[:POOL]
    )
    veteran_rotated = _rotate(veteran_pool)
    veteran, vet_imgs = _to_cards(
        veteran_rotated,
        foot_fn=lambda r: (f'{int(r.operating_years or 0)}년 운영', r.province or ''),
    )
    veteran = _pad(veteran, vet_imgs, {r.pk for r in veteran_rotated},
                   foot_fn=lambda r: (f'{int(r.operating_years or 0)}년 운영', r.province or ''))

    # ── 3. 가격 신뢰 100% ──
    price_pool = list(
        open_qs
        .filter(ai_profile__price_match_rate__gte=0.99, ai_profile__price_is_verified=True)
        .select_related('ai_profile')
        .order_by('-ai_profile__receipt_ocr_count')[:POOL]
    )
    if len(price_pool) < SHOW:
        price_pool = list(
            open_qs.filter(ai_profile__receipt_ocr_count__gt=0)
            .select_related('ai_profile')
            .order_by('-ai_profile__price_match_rate', '-ai_profile__receipt_ocr_count')[:POOL]
        )
    price_rotated = _rotate(price_pool)
    price_100, pr_imgs = _to_cards(
        price_rotated,
        foot_fn=lambda r: (
            f'영수증 {r.ai_profile.receipt_ocr_count:,}건',
            f'일치율 {round(r.ai_profile.price_match_rate * 100)}%',
        ),
    )
    price_100 = _pad(price_100, pr_imgs, {r.pk for r in price_rotated},
                     foot_fn=lambda r: (f'찜 {r.bm:,}개', ''))

    # ── 4. 이번 달 인증 폭발 ──
    def _get_verify_pool(since):
        return list(
            open_qs.select_related('ai_profile')
            .annotate(cnt=Count(
                'verifications',
                filter=Q(
                    verifications__status=ReceiptVerification.STATUS_APPROVED,
                    verifications__submitted_at__gte=since,
                )
            ))
            .filter(cnt__gt=0)
            .order_by('-cnt')[:POOL]
        )

    verify_pool = _get_verify_pool(month_start)
    verify_label = '이번 달'
    if len(verify_pool) < SHOW:
        verify_pool = _get_verify_pool(now - timedelta(days=90))
        verify_label = '90일'
    verify_rotated = _rotate(verify_pool)
    verify_surge, vf_imgs = _to_cards(
        verify_rotated,
        foot_fn=lambda r: (f'{verify_label} {r.cnt:,}건', r.province or ''),
    )
    verify_surge = _pad(verify_surge, vf_imgs, {r.pk for r in verify_rotated},
                        foot_fn=lambda r: (f'찜 {r.bm:,}개', r.province or ''))

    # ── 5. AI 추천 가게 ──
    ai_pool = list(
        open_qs
        .filter(ai_profile__ai_net_score__gte=3, ai_profile__review_count_analyzed__gte=3)
        .select_related('ai_profile')
        .order_by('-ai_profile__ai_net_score')[:POOL]
    )
    if len(ai_pool) < SHOW:
        ai_pool = list(
            open_qs.filter(ai_profile__review_count_analyzed__gte=1)
            .select_related('ai_profile')
            .order_by('-ai_profile__ai_net_score')[:POOL]
        )
    ai_rotated = _rotate(ai_pool)
    ai_top, ai_imgs = _to_cards(
        ai_rotated,
        foot_fn=lambda r: (
            f'AI {r.ai_profile.ai_net_score:+d}점',
            f'긍정 {round(r.ai_profile.positive_ratio * 100)}%',
        ),
    )
    ai_top = _pad(ai_top, ai_imgs, {r.pk for r in ai_rotated},
                  foot_fn=lambda r: (f'찜 {r.bm:,}개', ''))

    # ── 6. 동네별 저장수 TOP ──
    prov_qs = (
        open_qs.exclude(province='')
        .select_related('ai_profile')
        .annotate(bm=Count('bookmarks'))
        .order_by('province', '-bm')
    )
    seen_prov, prov_pool = set(), []
    for r in prov_qs[:500]:
        if r.province not in seen_prov:
            seen_prov.add(r.province)
            prov_pool.append(r)
            if len(prov_pool) >= POOL:
                break
    prov_rotated = _rotate(prov_pool)
    province_top, pv_imgs = _to_cards(
        prov_rotated,
        foot_fn=lambda r: (f'찜 {r.bm:,}개', r.province),
    )
    province_top = _pad(province_top, pv_imgs, {r.pk for r in prov_rotated},
                        foot_fn=lambda r: (f'찜 {r.bm:,}개', r.province or ''))

    # ── 7. 신상 가게 ──
    new_pool = list(
        open_qs.select_related('ai_profile')
        .filter(license_date__gte=one_yr)
        .order_by('-license_date')[:POOL]
    )
    new_rotated = _rotate(new_pool)
    new_shops, nw_imgs = _to_cards(
        new_rotated,
        foot_fn=lambda r: (
            f'{r.license_date.strftime("%Y.%m") if r.license_date else ""} 오픈', '',
        ),
    )
    new_shops = _pad(new_shops, nw_imgs, {r.pk for r in new_rotated},
                     foot_fn=lambda r: (f'{r.license_date.strftime("%Y.%m") if r.license_date else ""} 오픈', ''))

    # ── 8. 인기급상승 ──
    surge_pool = list(
        open_qs.select_related('ai_profile')
        .annotate(
            bm_total=Count('bookmarks'),
            bm_curr=Count('bookmarks', filter=Q(bookmarks__created_at__gte=thirty_ago)),
        )
        .filter(bm_total__gte=30, bm_curr__gt=0)
        .order_by('-bm_curr')[:POOL]
    )
    if len(surge_pool) < SHOW:
        surge_pool = list(
            open_qs.select_related('ai_profile')
            .annotate(
                bm_total=Count('bookmarks'),
                bm_curr=Count('bookmarks', filter=Q(bookmarks__created_at__gte=thirty_ago)),
            )
            .filter(bm_total__gte=1)
            .order_by('-bm_total')[:POOL]
        )
    surge_rotated = _rotate(surge_pool)
    surge, sg_imgs = _to_cards(
        surge_rotated,
        foot_fn=lambda r: (f'찜 {r.bm_total:,}개', r.province or ''),
    )
    surge = _pad(surge, sg_imgs, {r.pk for r in surge_rotated},
                 foot_fn=lambda r: (f'찜 {r.bm:,}개', r.province or ''))

    sections = [
        {'title': '업종별 저장수 TOP', 'badge': '업종 랭킹',    'cards': biz_top},
        {'title': '노포 명예의 전당',  'badge': '20년 이상',    'cards': veteran},
        {'title': '가격 신뢰 100%',   'badge': '가격 일치율',  'cards': price_100},
        {'title': '이번 달 인증 폭발', 'badge': '영수증 인증',  'cards': verify_surge},
        {'title': 'AI 추천 가게',     'badge': 'AI 분석',      'cards': ai_top},
        {'title': '동네별 저장수 TOP', 'badge': '지역 랭킹',    'cards': province_top},
        {'title': '신상 가게',         'badge': '최근 오픈',    'cards': new_shops},
        {'title': '인기급상승',        'badge': '찜수 급증',    'cards': surge},
    ]
    # 주간 섹션 순서 로테이션 — week_seed 기반으로 결정론적 셔플
    # 같은 주 안에서는 항상 동일한 순서, 매주 첫 방문 시 새로운 순서
    random.Random(week_seed).shuffle(sections)
    return sections


def _list_trust_level(r) -> int:
    """
    리스트 페이지용 신뢰 레벨 산출.

    LV1 🏆 : 90점↑ + LV2 조건 전부 + 최근 90일 심각 패널티 0건
    LV2 🌺🌺: 75~89점 + 방문인증 200↑ + 가격일치율 100% + 정부인증 1↑ + AI ≥+6 + 경고 없음
    LV3 🌺 : 55~74점 + 방문인증 100↑ + 가격일치율 95%↑(표본 30↑) + 위생경고 없음
    LV4 ⏳ : 나머지 (표본 30건 미만이면 최대 LV4)
    """
    try:
        ai_p = r.ai_profile
    except Exception:
        ai_p = None

    # ── 정부인증 / 기본 점수 ──────────────────────────────
    cert_count    = _calc_cert_count(r)
    govt_score    = min(cert_count * 5, 25)
    price_score   = ai_p.price_match_score if ai_p else 0
    price_rate    = (ai_p.price_match_rate or 0.0) if ai_p else 0.0
    receipt_count = ai_p.receipt_ocr_count if ai_p else 0
    ai_score      = ai_p.ai_net_score if ai_p else 0
    hygiene_alert = ai_p.hygiene_alert if ai_p else False

    verified_count = getattr(r, 'verified_count', 0)
    visit_score    = _lookup_score(verified_count, _VISIT_SCORE_TABLE)

    # ── 찜 점수 (리스트에서는 절대 건수 근사 — 퍼센타일 생략) ──
    bm = getattr(r, 'bookmark_count', 0)
    if   bm >= 50: like_score = 10
    elif bm >= 20: like_score = 8
    elif bm >= 10: like_score = 6
    elif bm >= 5:  like_score = 4
    elif bm >= 1:  like_score = 2
    else:          like_score = 0

    history_score = _lookup_score(r.operating_years or 0, _HISTORY_SCORE_TABLE)
    total         = govt_score + price_score + visit_score + like_score + history_score + ai_score

    # ── 레벨별 추가 조건 ───────────────────────────────────
    lv2_cond = (
        verified_count >= 200
        and price_rate >= 0.999
        and cert_count >= 1
        and ai_score >= 6
        and not hygiene_alert
    )
    lv3_cond = (
        verified_count >= 100
        and receipt_count >= 30
        and price_rate >= 0.95
        and not hygiene_alert
    )

    if total >= _LEVEL_MIN_SCORE[1] and lv2_cond and not hygiene_alert:
        return 1
    if total >= _LEVEL_MIN_SCORE[2] and lv2_cond:
        return 2
    if total >= _LEVEL_MIN_SCORE[3] and lv3_cond:
        return 3
    return 4


def _calc_level_score(restaurant, ai_profile):
    """레벨화 기준 6개 항목 점수 계산 및 레벨 판정."""

    # 1. 정부인증 (25점) — 인증 1개당 5점
    cert_count = _calc_cert_count(restaurant)
    govt_score = min(cert_count * 5, 25)

    # 2. 가격일치율 (20점)
    if ai_profile:
        price_score    = ai_profile.price_match_score
        price_verified = ai_profile.price_is_verified
        price_rate_pct = round((ai_profile.price_match_rate if ai_profile.price_match_rate is not None else 1.0) * 100)
        receipt_count  = ai_profile.receipt_ocr_count
    else:
        price_score = price_rate_pct = receipt_count = 0
        price_verified = False

    # 3. 방문자인증 (15점)
    verified_count = restaurant.verifications.filter(status=ReceiptVerification.STATUS_APPROVED).count()
    visit_score    = _lookup_score(verified_count, _VISIT_SCORE_TABLE)

    # 4. 찜수 (10점) — 동종 업종 내 백분위
    like_count = restaurant.bookmarks.count()
    like_pct_rank = 0  # "상위 N%" 표시용

    if like_count == 0:
        like_score = 0
    else:
        same_qs = PublicRestaurantData.objects.filter(
            status_code=PublicRestaurantData.STATUS_OPEN,
        )
        if restaurant.business_type:
            same_qs = same_qs.filter(business_type=restaurant.business_type)
        same_qs     = same_qs.annotate(bm_count=Count("bookmarks"))
        total_same  = same_qs.count()
        below_count = same_qs.filter(bm_count__lt=like_count).count()
        percentile  = (below_count / total_same * 100) if total_same else 100

        if   percentile >= 99: like_score = 10
        elif percentile >= 95: like_score = 8
        elif percentile >= 90: like_score = 6
        elif percentile >= 70: like_score = 4
        else:                  like_score = 2

        like_pct_rank = round(100 - percentile)

    # 5. 연혁 (20점)
    years         = restaurant.operating_years or 0
    history_score = _lookup_score(years, _HISTORY_SCORE_TABLE)

    # 6. AI점수 (10점, -10~+10)
    ai_score = ai_profile.ai_net_score if ai_profile else 0

    total = govt_score + price_score + visit_score + like_score + history_score + ai_score

    # 레벨 판정
    _LEVEL_META = {
        1: ("마스터 신뢰 가게", "🏆"),
        2: ("우수 신뢰 가게",   "🌺🌺"),
        3: ("신뢰 가게",        "🌺"),
        4: ("탐색중인 가게",    "⏳"),
    }
    if   total >= _LEVEL_MIN_SCORE[1]: level = 1
    elif total >= _LEVEL_MIN_SCORE[2]: level = 2
    elif total >= _LEVEL_MIN_SCORE[3]: level = 3
    else:                              level = 4
    level_name, level_icon = _LEVEL_META[level]

    next_thresholds = {4: _LEVEL_MIN_SCORE[3], 3: _LEVEL_MIN_SCORE[2], 2: _LEVEL_MIN_SCORE[1], 1: None}
    next_threshold  = next_thresholds[level]
    points_to_next  = (next_threshold - total) if next_threshold else 0
    progress_pct    = min(100, round(total))

    def _pct(score, max_score):
        return min(100, round(score / max_score * 100)) if max_score else 0

    return {
        "govt_score":      govt_score,   "govt_max":      25, "cert_count":     cert_count,
        "govt_pct":        _pct(govt_score, 25),
        "price_score":     price_score,  "price_max":     20, "price_verified": price_verified,
        "price_rate_pct":  price_rate_pct, "receipt_count": receipt_count,
        "price_pct":       _pct(price_score, 20),
        "visit_score":     visit_score,  "visit_max":     15, "verified_count": verified_count,
        "visit_pct":       _pct(visit_score, 15),
        "like_score":      like_score,   "like_max":      10,
        "like_count":      like_count,   "like_pct_rank": like_pct_rank,
        "like_pct":        _pct(like_score, 10),
        "history_score":   history_score,"history_max":   20, "operating_years": round(years, 1),
        "history_pct":     _pct(history_score, 20),
        "ai_score":        ai_score,     "ai_max":        10,
        "ai_pct":          _pct(ai_score + 10, 20),
        "total":           total,        "level":         level,
        "level_name":      level_name,   "level_icon":    level_icon,
        "points_to_next":  points_to_next, "next_threshold": next_threshold,
        "progress_pct":    progress_pct,
    }


class OwnerDashboardView(LoginRequiredMixin, TemplateView):
    """
    GET /dashboard/
    사장님·관리자 전용 대시보드 페이지.
    - 비로그인 → 로그인 페이지
    - 로그인했지만 owner/admin 아님 → 우리 가게 등록 페이지
    """
    template_name = "honest_restaurant/owner_dashboard.html"
    login_url     = "/accounts/login/"

    def handle_no_permission(self):
        return redirect(f"{LOGIN_URL}?next=/dashboard/")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            role = getattr(getattr(request.user, "profile", None), "role", "guest")
            if role not in ("owner", "admin"):
                return redirect("public_restaurants:register-restaurant")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        restaurant = getattr(self.request.user, "owned_restaurant", None)
        if not restaurant:
            return ctx

        try:
            ai_profile = restaurant.ai_profile
        except Exception:
            ai_profile = None

        ai_report       = restaurant.ai_reports.filter(status="done").first()
        recent_receipts = (
            restaurant.verifications
            .select_related("user")
            .order_by("-submitted_at")[:5]
        )

        score_data = _calc_level_score(restaurant, ai_profile)

        # 비율 (0~1 float → 0~100 int)
        positive_pct    = round((ai_profile.positive_ratio    or 0) * 100) if ai_profile else 0
        negative_pct    = round((ai_profile.negative_ratio    or 0) * 100) if ai_profile else 0
        neutral_pct     = max(0, 100 - positive_pct - negative_pct)
        alley_ratio_pct = round((ai_profile.alley_review_ratio or 0) * 100) if ai_profile else 0

        # 레이더 차트 데이터 (6개 항목 달성률 %)
        radar_data = json.dumps([
            score_data['govt_pct'],
            score_data['price_pct'],
            score_data['history_pct'],
            score_data['visit_pct'],
            score_data['like_pct'],
            score_data['ai_pct'],
        ])

        # 월별 영수증 인증 추이 (최근 6개월)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_receipts = (
            restaurant.verifications
            .filter(submitted_at__gte=six_months_ago)
            .annotate(month=TruncMonth('submitted_at'))
            .values('month')
            .annotate(cnt=Count('id'))
            .order_by('month')
        )
        trend_labels = json.dumps([str(r['month'])[:7] for r in monthly_receipts], ensure_ascii=False)
        trend_data   = json.dumps([r['cnt'] for r in monthly_receipts])

        # 월별 저장수 추이 (최근 6개월)
        monthly_bookmarks = (
            restaurant.bookmarks
            .filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(cnt=Count('id'))
            .order_by('month')
        )
        bm_trend_labels = json.dumps([str(r['month'])[:7] for r in monthly_bookmarks], ensure_ascii=False)
        bm_trend_data   = json.dumps([r['cnt'] for r in monthly_bookmarks])

        # 태그 목록 (상대 막대 너비 % 포함, 최대값 기준)
        pos_tags, neg_tags = [], []
        if ai_profile:
            pos_raw = ai_profile.top_positive_tags or {}
            neg_raw = ai_profile.top_negative_tags or {}
            max_pos = max(pos_raw.values(), default=1)
            max_neg = max(neg_raw.values(), default=1)
            for tag, cnt in list(pos_raw.items())[:5]:
                pos_tags.append({'tag': tag, 'count': cnt, 'pct': round(cnt / max_pos * 100)})
            for tag, cnt in list(neg_raw.items())[:5]:
                neg_tags.append({'tag': tag, 'count': cnt, 'pct': round(cnt / max_neg * 100)})

        # 리포트 본문 — neg_tags 키워드를 빨간색으로 하이라이트
        report_text_html = None
        if ai_report and ai_report.report_text:
            text = escape(ai_report.report_text)
            for item in neg_tags:
                kw = escape(item['tag'])
                text = text.replace(kw, f'<strong style="color:var(--red)">{kw}</strong>', 1)
            report_text_html = mark_safe(text)

        # 루키 배지 (영업 1년 미만)
        operating_years    = score_data['operating_years']
        is_rookie          = 0 < operating_years < 1
        rookie_months_left = max(0, round((1 - operating_years) * 12)) if is_rookie else 0

        # 인기급상승 배지 (최근 30일 찜 증가율) — 2쿼리 → 1쿼리
        now        = timezone.now()
        thirty_ago = now - timedelta(days=30)
        sixty_ago  = now - timedelta(days=60)
        bm_agg = restaurant.bookmarks.aggregate(
            curr=Count("pk", filter=Q(created_at__gte=thirty_ago)),
            prev=Count("pk", filter=Q(created_at__gte=sixty_ago, created_at__lt=thirty_ago)),
        )
        curr_bm = bm_agg["curr"]
        prev_bm = bm_agg["prev"]
        if curr_bm < 30:
            trending_pct = 0
        elif prev_bm > 0:
            trending_pct = round(curr_bm / prev_bm * 100)
        else:
            trending_pct = 200
        is_trending      = trending_pct >= 200
        trending_bar_pct = min(100, round(trending_pct / 200 * 100))
        trending_needed  = max(0, 200 - trending_pct)

        ctx.update({
            "restaurant":        restaurant,
            "ai_profile":        ai_profile,
            "ai_report":         ai_report,
            "score_data":        score_data,
            "recent_receipts":   recent_receipts,
            "alley_ratio_pct":   alley_ratio_pct,
            "positive_pct":      positive_pct,
            "negative_pct":      negative_pct,
            "neutral_pct":       neutral_pct,
            "radar_data":        radar_data,
            "trend_labels":      trend_labels,
            "trend_data":        trend_data,
            "bm_trend_labels":   bm_trend_labels,
            "bm_trend_data":     bm_trend_data,
            "pos_tags":          pos_tags,
            "neg_tags":          neg_tags,
            "report_text_html":  report_text_html,
            "is_rookie":         is_rookie,
            "rookie_months_left": rookie_months_left,
            "trending_pct":      trending_pct,
            "is_trending":       is_trending,
            "trending_bar_pct":  trending_bar_pct,
            "trending_needed":   trending_needed,
            # 경보 배너 플래그
            "show_hygiene_alert": bool(ai_profile and ai_profile.hygiene_alert),
            "show_price_alert":   bool(ai_profile and not ai_profile.price_is_verified),
        })

        from marketing.ai_service import get_active_platforms
        ctx['active_platforms'] = get_active_platforms()
        ctx['sns_connected']    = bool(restaurant and restaurant.sns_connected)

        return ctx


class RegisterRestaurantView(LoginRequiredMixin, View):
    """
    GET  /register-restaurant/  — 검색 폼 + 결과 표시
    POST /register-restaurant/  — 선택한 식당을 우리 가게로 등록
    이미 owner인 경우 대시보드로 이동한다.
    """
    login_url = LOGIN_URL

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            role = getattr(getattr(request.user, "profile", None), "role", "guest")
            if role in ("owner", "admin"):
                return redirect("public_restaurants:owner-dashboard")
            if RestaurantOwnerApplication.objects.filter(
                user=request.user,
                status=RestaurantOwnerApplication.STATUS_PENDING,
            ).exists():
                return HttpResponse(_PENDING_JS)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        query = request.GET.get("q", "").strip()
        results = []
        if query:
            results = (
                PublicRestaurantData.objects
                .filter(
                    Q(name__icontains=query) | Q(address_road__icontains=query),
                    status_code=PublicRestaurantData.STATUS_OPEN,
                    owner__isnull=True,
                )
                .only("id", "name", "address_road", "business_type", "license_date")
                [:20]
            )
        return render(request, "honest_restaurant/register_restaurant.html", {
            "query":   query,
            "results": results,
        })

    def post(self, request):
        restaurant_id = request.POST.get("restaurant_id")
        if not restaurant_id:
            return redirect("public_restaurants:register-restaurant")

        get_object_or_404(
            PublicRestaurantData,
            pk=restaurant_id,
            owner__isnull=True,
            status_code=PublicRestaurantData.STATUS_OPEN,
        )
        return redirect("public_restaurants:verify-ownership", pk=restaurant_id)


_ACCEPTED_JS = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
alert('신청이 접수되었습니다.\\n관리자 확인 후 1~2 영업일 내에 처리됩니다.');
window.location.href = '/';
</script>
</body></html>"""

_PENDING_JS = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
alert('사업자 인증 검토 중입니다.\\n\\n신청하신 가게를 담당자가 확인하고 있어요.\\n승인 완료 시 매장 대시보드를 바로 이용하실 수 있습니다.');
window.location.href = '/';
</script>
</body></html>"""


class OwnerVerifyView(LoginRequiredMixin, View):
    """
    GET  /register-restaurant/<pk>/verify/  — 사업자등록번호 입력 폼
    POST action=verify  — 국세청 API → 계속사업자 확인 후 신청 접수
    POST action=upload  — 사업자등록증 업로드 → 신청 접수
    두 경로 모두 관리자 승인 후 owner 권한이 부여된다.
    """
    login_url = LOGIN_URL

    def _get_restaurant(self, pk):
        return get_object_or_404(
            PublicRestaurantData,
            pk=pk,
            owner__isnull=True,
            status_code=PublicRestaurantData.STATUS_OPEN,
        )

    def _check_duplicate(self, restaurant, user):
        return RestaurantOwnerApplication.objects.filter(
            restaurant=restaurant,
            user=user,
            status=RestaurantOwnerApplication.STATUS_PENDING,
        ).exists()

    def get(self, request, pk):
        restaurant = self._get_restaurant(pk)
        return render(request, "honest_restaurant/verify_ownership.html", {
            "restaurant": restaurant,
        })

    def post(self, request, pk):
        restaurant = self._get_restaurant(pk)
        action = request.POST.get("action")

        # ── 1안: 국세청 API 검증 후 신청 접수 ───────────────────
        if action == "verify":
            b_no   = request.POST.get("business_number", "").strip()
            result = verify_business_number(b_no)

            if not (result["success"] and result["is_active"]):
                # API 실패 또는 계속사업자 아님 → 사업자등록증 업로드로 안내
                if result["success"] and not result["is_active"]:
                    error = f"사업자 상태가 '{result['status_text']}'입니다. 계속사업자만 등록할 수 있습니다."
                else:
                    error = result.get("error", "국세청 조회에 실패했습니다.")
                return render(request, "honest_restaurant/verify_ownership.html", {
                    "restaurant":      restaurant,
                    "business_number": b_no,
                    "verify_error":    error,
                    "show_upload":     True,
                })

            if self._check_duplicate(restaurant, request.user):
                return render(request, "honest_restaurant/verify_ownership.html", {
                    "restaurant":   restaurant,
                    "verify_error": "이미 검토 중인 신청이 있습니다. 관리자 승인을 기다려주세요.",
                })

            RestaurantOwnerApplication.objects.create(
                restaurant=restaurant,
                user=request.user,
                business_number=b_no,
                verified_by_api=True,
            )
            return HttpResponse(_ACCEPTED_JS)

        # ── 2안: 사업자등록증 업로드 ─────────────────────────────
        if action == "upload":
            b_no  = request.POST.get("business_number", "").strip()
            image = request.FILES.get("cert_image")
            if not image:
                return render(request, "honest_restaurant/verify_ownership.html", {
                    "restaurant":   restaurant,
                    "business_number": b_no,
                    "show_upload":  True,
                    "upload_error": "사업자등록증 사진을 첨부해주세요.",
                })

            if self._check_duplicate(restaurant, request.user):
                return render(request, "honest_restaurant/verify_ownership.html", {
                    "restaurant":   restaurant,
                    "show_upload":  True,
                    "upload_error": "이미 검토 중인 신청이 있습니다. 관리자 승인을 기다려주세요.",
                })

            RestaurantOwnerApplication.objects.create(
                restaurant=restaurant,
                user=request.user,
                business_number=b_no,
                cert_image=image,
                verified_by_api=False,
            )
            return HttpResponse(_ACCEPTED_JS)

        return redirect("public_restaurants:register-restaurant")


class RestaurantListView(LoginRequiredMixin, ListView):
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
    login_url           = "/accounts/login/"

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
        now        = timezone.now()
        thirty_ago = now - timedelta(days=30)
        sixty_ago  = now - timedelta(days=60)

        bm_sq = (
            Bookmark.objects
            .filter(restaurant_id=OuterRef("pk"))
            .order_by().values("restaurant_id")
            .annotate(n=Count("pk")).values("n")
        )
        vc_sq = (
            ReceiptVerification.objects
            .filter(restaurant_id=OuterRef("pk"), status=ReceiptVerification.STATUS_APPROVED)
            .order_by().values("restaurant_id")
            .annotate(n=Count("pk")).values("n")
        )
        curr_bm_sq = (
            Bookmark.objects
            .filter(restaurant_id=OuterRef("pk"), created_at__gte=thirty_ago)
            .order_by().values("restaurant_id")
            .annotate(n=Count("pk")).values("n")
        )
        prev_bm_sq = (
            Bookmark.objects
            .filter(restaurant_id=OuterRef("pk"),
                    created_at__gte=sixty_ago, created_at__lt=thirty_ago)
            .order_by().values("restaurant_id")
            .annotate(n=Count("pk")).values("n")
        )
        qs = (
            PublicRestaurantData.objects
            .filter(status_code=self._OPEN)
            .defer("management_no", "area", "last_modified_at",
                   "sanitation_business_type", "created_at")
            .select_related("ai_profile")
            .annotate(
                bookmark_count=Coalesce(Subquery(bm_sq,      output_field=IntegerField()), 0),
                verified_count=Coalesce(Subquery(vc_sq,      output_field=IntegerField()), 0),
                curr_bm=       Coalesce(Subquery(curr_bm_sq, output_field=IntegerField()), 0),
                prev_bm=       Coalesce(Subquery(prev_bm_sq, output_field=IntegerField()), 0),
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

        # 신뢰 레벨 + 특수 배지 부착 (select_related로 N+1 없음)
        for r in ctx["object_list"]:
            r.trust_level = _list_trust_level(r)

            try:
                ai_p = r.ai_profile
            except Exception:
                ai_p = None

            years = r.operating_years or 0
            r.badge_alley   = bool(ai_p and ai_p.is_alley_eligible)
            r.badge_rookie  = 0 < years < 1
            curr = r.curr_bm
            prev = r.prev_bm
            r.badge_trending = (curr >= 30) and (
                (prev > 0 and curr / prev >= 2) or (prev == 0 and curr >= 30)
            )

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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RestaurantDetailView(LoginRequiredMixin, DetailView):
    """
    GET /restaurants/<pk>/
    Query params: ?sort=latest|score_high|score_low
    """

    template_name       = "honest_restaurant/restaurant_detail.html"
    context_object_name = "restaurant"
    login_url           = "/accounts/login/"

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

        # ── 리뷰 목록 (정렬 + 사용자 별점 annotate + 페이지네이션) ──
        sort     = self.request.GET.get("sort", "latest")
        ordering = self._SORT_MAP.get(sort, "-created_at")

        user_score_sq = Subquery(
            Rating.objects
            .filter(restaurant=restaurant, user=OuterRef("user"))
            .values("score")[:1]
        )
        reviews_qs = (
            restaurant.interaction_reviews
            .select_related("user")
            .annotate(user_score=user_score_sq)
            .order_by(ordering)
        )

        page_num  = max(1, int(self.request.GET.get("page", 1) or 1))
        paginator = CachedPaginator(
            reviews_qs, 10,
            cache_key=f"review_count_{restaurant.pk}_{sort}",
            cache_ttl=60,
        )
        reviews        = paginator.get_page(page_num)
        review_total   = paginator.count
        review_pg_nums = page_range(paginator, page_num)

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

        # 본인 가게 여부 — staff 또는 자신이 owner인 가게만 편집 가능
        owned = getattr(user, "owned_restaurant", None) if user.is_authenticated else None
        is_my_restaurant = user.is_authenticated and (
            user.is_staff or (owned is not None and owned.pk == restaurant.pk)
        )

        menu_items = list(
            RestaurantMenuItem.objects
            .filter(restaurant=restaurant)
            .values("pk", "name", "price")
        )

        # ── 앨범 그리드용 통합 이미지 목록 (미디어 + 리뷰, 최신순) ──
        album_images = []
        for m in restaurant.media.filter(media_type="image"):
            album_images.append({"url": m.file.url, "ts": m.uploaded_at})
        for rev in restaurant.interaction_reviews.only("image", "image_2", "image_3", "created_at"):
            for field in ("image", "image_2", "image_3"):
                img = getattr(rev, field)
                if img:
                    album_images.append({"url": img.url, "ts": rev.created_at})
        album_images.sort(key=lambda x: x["ts"], reverse=True)

        try:
            ai_profile = restaurant.ai_profile
        except Exception:
            ai_profile = None

        price_match_pct = None
        if ai_profile and ai_profile.receipt_ocr_count > 0:
            price_match_pct = round(ai_profile.price_match_rate * 100)

        score_data = _calc_level_score(restaurant, ai_profile)

        # ── 특수 배지 ────────────────────────────────────────
        operating_years = score_data["operating_years"]
        is_rookie = 0 < operating_years < 1

        now        = timezone.now()
        thirty_ago = now - timedelta(days=30)
        sixty_ago  = now - timedelta(days=60)
        bm_agg = restaurant.bookmarks.aggregate(
            curr=Count("pk", filter=Q(created_at__gte=thirty_ago)),
            prev=Count("pk", filter=Q(created_at__gte=sixty_ago, created_at__lt=thirty_ago)),
        )
        curr_bm = bm_agg["curr"]
        prev_bm = bm_agg["prev"]
        if curr_bm < 30:
            is_trending = False
        elif prev_bm > 0:
            is_trending = (curr_bm / prev_bm) >= 2
        else:
            is_trending = True

        ctx.update({
            "reviews"            : reviews,
            "review_total"       : review_total,
            "review_pg_nums"     : review_pg_nums,
            "page_num"           : page_num,
            "media_list"         : restaurant.media.order_by("-uploaded_at"),
            "album_images"       : album_images,
            "has_verified"       : has_verified,
            "can_write"          : has_verified and not is_my_restaurant,
            "sort"               : sort,
            "verification_count" : verification_count,
            "menu_items"         : menu_items,
            "my_review"   : (
                Review.objects.filter(user=user, restaurant=restaurant).first()
                if user.is_authenticated else None
            ),
            "is_bookmarked": (
                Bookmark.objects.filter(user=user, restaurant=restaurant).exists()
                if user.is_authenticated else False
            ),
            "is_managed"       : is_managed,
            "is_my_restaurant" : is_my_restaurant,
            "ai_profile"       : ai_profile,
            "price_match_pct"  : price_match_pct,
            "score_data"       : score_data,
            "is_rookie"        : is_rookie,
            "is_trending"      : is_trending,
            "tagline"          : restaurant.tagline or _generate_tagline(),
            "tagline_update_url": reverse("public_restaurants:tagline-update", args=[restaurant.pk]),
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

        cache_key = "districts_" + hashlib.md5(province.encode()).hexdigest()[:8]
        cached = cache.get(cache_key)
        if cached is not None:
            return JsonResponse({"districts": cached})

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

        result = sorted(districts)
        cache.set(cache_key, result, 60 * 60 * 24)  # 24시간 (행정구역은 거의 안 바뀜)
        return JsonResponse({"districts": result})


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


class OwnerOrStaffRequiredMixin:
    """
    사장님(UserProfile.role=owner) 또는 staff만 허용.
    사장님은 본인이 소유한 가게(URL pk)에서만 작업 가능.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)

        profile = getattr(request.user, "profile", None)
        role = getattr(profile, "role", "guest")

        if role not in ("owner", "admin"):
            return JsonResponse({"detail": "권한이 없습니다."}, status=403)

        # 사장님은 본인 가게만 수정 가능
        if role == "owner":
            pk = self.kwargs.get("pk")
            if pk:
                owned = getattr(request.user, "owned_restaurant", None)
                if owned is None or str(owned.pk) != str(pk):
                    return JsonResponse({"detail": "내 가게에서만 이용할 수 있습니다."}, status=403)

        return super().dispatch(request, *args, **kwargs)


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
        verification, _ = ReceiptVerification.objects.update_or_create(
            restaurant=restaurant,
            user=request.user,
            defaults={
                "receipt_image": form.cleaned_data["receipt_image"],
                "comment"      : form.cleaned_data.get("comment", ""),
                "status"       : ReceiptVerification.STATUS_APPROVED,
            },
        )

        # OCR + 가격 비교 비동기 처리
        from ai.ai_ocr.tasks import analyze_receipt as _ocr_task
        _ocr_task.delay(verification.pk)

        redirect_url = (
            reverse("public_restaurants:restaurant-detail-page", kwargs={"pk": pk})
            + "#review-section"
        )
        if self._is_ajax(request):
            return JsonResponse({"success": True, "redirect": redirect_url})
        return redirect(redirect_url)


class MenuItemCreateView(AjaxLoginRequiredMixin, OwnerOrStaffRequiredMixin, View):
    """
    POST /restaurants/<pk>/menu-items/
    사장님/관리자가 메뉴명·가격을 직접 입력해 등록한다.
    """

    def post(self, request, pk):
        restaurant = get_object_or_404(PublicRestaurantData, pk=pk)
        form = MenuItemForm(request.POST)

        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        item, created = RestaurantMenuItem.objects.update_or_create(
            restaurant=restaurant,
            name=form.cleaned_data["name"],
            defaults={"price": form.cleaned_data["price"]},
        )
        if created:
            max_order = (
                RestaurantMenuItem.objects
                .filter(restaurant=restaurant)
                .aggregate(m=Max("order"))["m"] or 0
            )
            item.order = max_order
            item.save(update_fields=["order"])
        return JsonResponse({
            "success": True,
            "id": item.pk,
            "name": item.name,
            "price": item.price,
            "created": created,
        })


class MenuItemUpdateView(AjaxLoginRequiredMixin, OwnerOrStaffRequiredMixin, View):
    """
    POST /restaurants/<pk>/menu-items/<item_pk>/update/
    메뉴명·가격을 수정한다. unique_together 충돌은 ModelForm이 검증.
    """

    def post(self, request, pk, item_pk):
        item = get_object_or_404(RestaurantMenuItem, pk=item_pk, restaurant__pk=pk)
        form = MenuItemForm(request.POST, instance=item)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)
        updated = form.save()
        return JsonResponse({
            "success": True,
            "id": updated.pk,
            "name": updated.name,
            "price": updated.price,
        })


class MenuItemDeleteView(AjaxLoginRequiredMixin, OwnerOrStaffRequiredMixin, View):
    """
    POST /restaurants/<pk>/menu-items/<item_pk>/delete/
    """

    def post(self, request, pk, item_pk):
        item = get_object_or_404(RestaurantMenuItem, pk=item_pk, restaurant__pk=pk)
        item.delete()
        return JsonResponse({"success": True})


class RestaurantInfoUpdateView(AjaxLoginRequiredMixin, OwnerOrStaffRequiredMixin, View):
    """
    POST /restaurants/<pk>/info/update/
    도로명주소·지번주소·전화번호를 수정한다.
    """

    def post(self, request, pk):
        restaurant = get_object_or_404(PublicRestaurantData, pk=pk)
        form = RestaurantInfoForm(request.POST, instance=restaurant)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)
        updated = form.save(commit=False)
        updated.save(update_fields=["address_road", "address_jibun", "phone"])
        return JsonResponse({
            "success"      : True,
            "address_road" : updated.address_road,
            "address_jibun": updated.address_jibun,
            "phone"        : updated.phone,
        })


_TAGLINE_POOL = [
    "오늘도 정직한 재료로, 진심을 담아 요리합니다.",
    "동네 단골이 먼저 알아본 맛집입니다.",
    "가격도, 재료도, 마음도 정직한 가게입니다.",
    "매일 새벽부터 준비하는 손맛을 자신합니다.",
    "단 한 번의 방문으로 단골이 되는 가게입니다.",
    "정직한 가격, 푸짐한 양, 변하지 않는 맛.",
    "국내산 재료만 사용하는 원칙을 지킵니다.",
    "오늘의 영수증이 내일의 신뢰가 됩니다.",
    "화학조미료 없이, 정성만으로 끓여냅니다.",
    "우리 동네를 대표하는 맛으로 기억되고 싶습니다.",
    "첫 방문부터 편안한 단골처럼 모십니다.",
    "매일 아침 장을 보는 신선함이 자랑입니다.",
    "진짜 맛은 숨길 수 없다고 믿습니다.",
    "오랜 세월이 만들어낸 손맛을 이어갑니다.",
    "가게 문을 열 때마다 최선을 다합니다.",
    "줄을 서더라도 다시 찾는 이유가 있습니다.",
    "저렴하지만 절대 싸구려는 아닙니다.",
    "주방이 투명할 자신이 있습니다.",
    "오늘도 내 가족에게 내놓을 수 있는 음식을 만듭니다.",
    "한 그릇에 담긴 수십 년의 정성입니다.",
    "정직식당이 보증하는 동네의 진심입니다.",
    "SNS보다 입소문으로 더 유명한 집입니다.",
    "맛있는 건 단순합니다. 좋은 재료, 정직한 손.",
    "이 거리에서 가장 오래 살아남은 이유가 있습니다.",
    "지역 농가와 함께 식재료를 직거래합니다.",
    "영업 시작부터 지금까지 레시피 하나 안 바꿨습니다.",
    "단 하나의 메뉴에 모든 것을 담았습니다.",
    "이 동네 맛의 역사를 함께 만들어가고 있습니다.",
    "싱싱한 재료, 합리적인 가격, 변함없는 정성.",
    "오늘도 단골손님의 기대를 저버리지 않겠습니다.",
]


def _generate_tagline() -> str:
    return random.choice(_TAGLINE_POOL)


class TaglineUpdateView(AjaxLoginRequiredMixin, OwnerOrStaffRequiredMixin, View):
    """
    POST /restaurants/<pk>/tagline/update/
    Body (JSON): {"tagline": "..."} — 직접 수정
    GET  /restaurants/<pk>/tagline/update/?regen=1 — 자동 생성
    """

    def get(self, request, pk):
        restaurant = get_object_or_404(PublicRestaurantData, pk=pk)
        new_tagline = _generate_tagline()
        restaurant.tagline = new_tagline
        restaurant.save(update_fields=['tagline'])
        return JsonResponse({"success": True, "tagline": new_tagline})

    def post(self, request, pk):
        restaurant = get_object_or_404(PublicRestaurantData, pk=pk)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"detail": "JSON 파싱 오류"}, status=400)
        tagline = data.get("tagline", "").strip()
        if len(tagline) > 200:
            return JsonResponse({"detail": "200자 이내로 입력해 주세요."}, status=400)
        restaurant.tagline = tagline
        restaurant.save(update_fields=['tagline'])
        return JsonResponse({"success": True, "tagline": restaurant.tagline})


class MenuItemReorderView(AjaxLoginRequiredMixin, OwnerOrStaffRequiredMixin, View):
    """
    POST /restaurants/<pk>/menu-items/reorder/
    Body (JSON): {"pks": [3, 1, 2]}
    """

    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            pks = data.get("pks", [])
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"detail": "JSON 파싱 오류"}, status=400)

        if not isinstance(pks, list):
            return JsonResponse({"detail": "pks는 배열이어야 합니다."}, status=400)

        with transaction.atomic():
            for order_idx, pk_val in enumerate(pks):
                RestaurantMenuItem.objects.filter(
                    pk=pk_val, restaurant__pk=pk
                ).update(order=order_idx)

        return JsonResponse({"success": True})


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

