from celery import shared_task

from . import services


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def classify_review(self, review_id: int, text: str) -> None:
    """
    리뷰 분류 비동기 태스크.
    분류 성공 후 식당 AI 프로필 집계를 자동으로 연결(chain)한다.
    """
    try:
        services.request_review_classification(review_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)

    # 분류 완료 후 식당 단위 집계 갱신
    from interactions.models import Review
    restaurant_id = (
        Review.objects
        .values_list("restaurant_id", flat=True)
        .get(pk=review_id)
    )
    recalculate_ai_profile.delay(restaurant_id)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def recalculate_ai_profile(self, restaurant_id: int) -> None:
    """
    식당 AI 프로필(골목장인 자격·AI 점수·대시보드 태그)을 집계·갱신한다.
    리뷰 분류 완료 후 자동 호출되며, 관리자가 수동으로 트리거할 수도 있다.
    """
    from .aggregator import aggregate_restaurant_ai
    try:
        aggregate_restaurant_ai(restaurant_id)
    except Exception as exc:
        raise self.retry(exc=exc)
