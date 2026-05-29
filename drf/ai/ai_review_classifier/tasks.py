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
    # interactions 앱이 이 tasks를 import할 수 있으므로 최상단에 두면 순환 import 발생
    from interactions.models import Review
    try:
        restaurant_id = (
            Review.objects
            .values_list("restaurant_id", flat=True)
            .get(pk=review_id)
        )
    except Review.DoesNotExist:
        return  # 분류 완료 전 리뷰가 삭제된 경우 집계 생략
    recalculate_ai_profile.delay(restaurant_id)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def recalculate_ai_profile(self, restaurant_id: int) -> None:
    """
    식당 AI 프로필(골목장인 자격·AI 점수·대시보드 태그)을 집계·갱신한다.
    리뷰 분류 완료 후 자동 호출되며, 관리자가 수동으로 트리거할 수도 있다.
    """
    # aggregator가 honest_restaurant 등 여러 앱을 import하므로 앱 로딩 완료 후 지연 import
    from .aggregator import aggregate_restaurant_ai
    try:
        aggregate_restaurant_ai(restaurant_id)
    except Exception as exc:
        raise self.retry(exc=exc)
