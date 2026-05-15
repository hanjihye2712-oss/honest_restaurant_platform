"""
honest_restaurant.pagination
============================
페이지네이션 관련 클래스와 헬퍼 함수를 한 곳에 모아 관리한다.

    CachedPaginator          — COUNT(*) 결과를 캐시하는 Django Paginator
    RestaurantCursorPagination — DRF API 전용 커서 기반 페이지네이션
    page_range               — 스마트 페이지 번호 목록 계산 함수
"""

from django.core.cache import cache
from django.core.paginator import Paginator
from django.utils.functional import cached_property

from rest_framework.pagination import CursorPagination as DRFCursorPagination


# ── Django ListView용 ─────────────────────────────────────────────────────────

class CachedPaginator(Paginator):
    """
    COUNT(*) 결과를 캐시하는 Paginator.

    문제: Django 기본 Paginator는 매 요청마다 COUNT(*)를 실행한다.
         데이터가 많을수록 이 쿼리가 전체 응답 시간을 지배한다.
    해결: 동일 필터 조합의 COUNT 결과를 cache_ttl 초 동안 재사용한다.
    """

    def __init__(self, object_list, per_page, *, cache_key, cache_ttl=300, **kwargs):
        super().__init__(object_list, per_page, **kwargs)
        self._cache_key = cache_key
        self._cache_ttl = cache_ttl

    @cached_property
    def count(self):
        cached = cache.get(self._cache_key)
        if cached is not None:
            return cached
        n = super().count
        cache.set(self._cache_key, n, self._cache_ttl)
        return n


# ── DRF ViewSet용 ─────────────────────────────────────────────────────────────

class RestaurantCursorPagination(DRFCursorPagination):
    """
    DRF API 전용 커서 기반 페이지네이션.

    문제: OFFSET 방식은 페이지가 깊을수록 DB가 이전 행을 모두 건너뛰어야 한다.
         예) 1,000페이지 = 19,980행 스캔 후 20행 반환 → O(n) 비용.
    해결: 마지막으로 받은 레코드의 id(커서)를 기준으로
         WHERE id < cursor 조건을 걸어 항상 O(1) 속도를 보장한다.

    사용: GET /api/public-restaurants/?cursor=<token>&page_size=20
    """

    page_size             = 15
    page_size_query_param = "page_size"
    max_page_size         = 100
    ordering              = "-id"   # PK → 항상 고유 인덱스 보장


# ── 템플릿용 헬퍼 ─────────────────────────────────────────────────────────────

def page_range(paginator, page_num, wing=3, max_page=None):
    """
    현재 페이지 ±wing + 첫/마지막 페이지 + 생략 표시(None) 목록 반환.

    예) 총 7,500페이지, 현재 50페이지, wing=3
        → [1, None, 47, 48, 49, 50, 51, 52, 53, None, 7500]

    None은 템플릿에서 '…' 생략 표시로 렌더링한다.
    max_page를 지정하면 그 이상의 페이지 링크를 생성하지 않는다.
    (뷰의 _MAX_PAGE 제한과 연동해 404 방지)
    """
    total = paginator.num_pages
    if max_page:
        total = min(total, max_page)

    near  = set(range(max(1, page_num - wing), min(total, page_num + wing) + 1))
    near |= {1, total}

    result, prev = [], None
    for p in sorted(near):
        if prev and p - prev > 1:
            result.append(None)   # 생략 표시 (…)
        result.append(p)
        prev = p

    return result
