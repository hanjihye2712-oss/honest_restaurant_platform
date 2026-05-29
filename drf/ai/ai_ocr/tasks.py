import logging

from celery import shared_task

from . import services

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def analyze_receipt(self, verification_id: int) -> None:
    """영수증 OCR + 사장님 등록 가격 비교 태스크."""
    try:
        services.analyze_receipt(verification_id)
    except Exception as exc:
        raise self.retry(exc=exc)
