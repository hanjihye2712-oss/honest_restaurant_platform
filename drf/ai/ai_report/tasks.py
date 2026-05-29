import logging

from celery import shared_task

from . import services

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def generate_restaurant_report(self, restaurant_id: int) -> None:
    """
    단일 식당 AI 리포트 생성 태스크.
    수동 트리거 또는 generate_all_reports에서 호출된다.
    """
    try:
        services.generate_report(restaurant_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def generate_all_reports() -> None:
    """
    AI 프로필이 있는 전체 식당 리포트를 일괄 생성한다.
    Celery Beat로 매주 월요일 새벽 6시에 실행한다.
    """
    # ai_review_classifier 앱과 ai_report 앱이 서로를 참조하므로 지연 import
    from ai.ai_review_classifier.models import RestaurantAIProfile

    restaurant_ids = list(
        RestaurantAIProfile.objects
        .filter(review_count_analyzed__gte=1)
        .values_list("restaurant_id", flat=True)
    )
    logger.info("일괄 리포트 생성 시작: 대상 식당 %d개", len(restaurant_ids))

    for rid in restaurant_ids:
        generate_restaurant_report.delay(rid)
