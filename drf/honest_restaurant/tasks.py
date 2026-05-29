"""
honest_restaurant.tasks
=======================
메인 페이지 캐시 사전 갱신 태스크.

    warm_index_cache — 메인 8개 섹션 데이터를 캐시 만료 전에 미리 빌드

Celery Beat 스케줄 (settings.py):
    50분 주기 실행 → _INDEX_CACHE_TTL(1시간)보다 짧게 유지해 cold-start 방지.
    Celery가 중단되더라도 최대 1시간은 기존 캐시가 서빙된다.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def warm_index_cache(self) -> None:
    """
    메인 페이지 8개 섹션 데이터를 미리 빌드해 캐시를 갱신한다.

    - 성공: Redis에 _INDEX_CACHE_TTL(1시간)로 저장
    - 실패: 최대 2회 재시도 (60초 간격)
    - 재시도 모두 실패: 기존 캐시가 만료될 때까지 유지되다가 cold-start 발생
    """
    try:
        from django.core.cache import cache
        from honest_restaurant.views import _INDEX_CACHE_KEY, _INDEX_CACHE_TTL, _build_index_sections

        sections = _build_index_sections()
        cache.set(_INDEX_CACHE_KEY, sections, _INDEX_CACHE_TTL)
        logger.info("warm_index_cache 완료 — %d개 섹션 캐시 갱신", len(sections))
    except Exception as exc:
        logger.error("warm_index_cache 실패 — %s", exc)
        raise self.retry(exc=exc)
