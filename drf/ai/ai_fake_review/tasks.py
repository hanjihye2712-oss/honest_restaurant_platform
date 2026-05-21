from celery import shared_task
from . import services


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_fake_review(self, review_id: int, korean_text: str) -> None:
    """
    가짜 리뷰 탐지 비동기 태스크.
    실패 시 최대 3회 60초 간격 재시도. 로깅은 services.py에서 처리.
    """
    try:
        services.request_fake_review_check(review_id, korean_text)
    except Exception as exc:
        raise self.retry(exc=exc)
