from django.db import migrations


class Migration(migrations.Migration):
    """
    SentimentResult 모델을 ai 앱으로 이동했으므로 interactions state에서 제거.
    DB 테이블은 ai 앱이 관리하므로 DROP 하지 않는다.
    """

    dependencies = [
        ('interactions', '0002_add_sentiment_result'),
        ('ai', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='SentimentResult'),
            ],
            database_operations=[],  # 테이블 유지 — DB 작업 없음
        ),
    ]
