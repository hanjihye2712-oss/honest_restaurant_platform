from celery import shared_task

from honest_restaurant.views import SeoulRestaurantSyncer


@shared_task
def daily_sync():
    syncer = SeoulRestaurantSyncer()
    rows   = syncer.fetch(1, SeoulRestaurantSyncer.BATCH_SIZE)
    syncer.save(rows)