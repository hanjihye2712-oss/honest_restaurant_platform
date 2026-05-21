from celery import shared_task
from . import services


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_sentiment(self, review_id: int, text: str) -> None:
    """
    리뷰 감성 분석 비동기 태스크.
    실패 시 최대 3회 60초 간격으로 재시도한다.
    오류 로깅은 services.py에서 처리하므로 여기서는 재시도만 담당한다.
    """
    try:
        services.request_sentiment(review_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)
