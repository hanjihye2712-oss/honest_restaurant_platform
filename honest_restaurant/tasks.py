from celery import shared_task
from .services.seoul_api import fetch_restaurants, save_restaurants, BATCH_SIZE

@shared_task
def daily_sync():
    rows = fetch_restaurants(1, BATCH_SIZE)
    save_restaurants(rows)