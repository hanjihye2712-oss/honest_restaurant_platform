import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    SentimentResult 모델을 interactions 앱에서 ai 앱으로 이동.
    DB 테이블(sentiment_result)은 이미 존재하므로 state만 등록하고 DB는 건드리지 않는다.
    """

    initial = True

    dependencies = [
        ('interactions', '0002_add_sentiment_result'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='SentimentResult',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('status', models.CharField(
                            choices=[('pending', '분석 대기'), ('done', '분석 완료'), ('failed', '분석 실패')],
                            db_index=True, default='pending', max_length=10, verbose_name='분석 상태',
                        )),
                        ('label', models.CharField(blank=True, help_text='긍정 / 부정', max_length=10, null=True, verbose_name='감정 레이블')),
                        ('score', models.FloatField(blank=True, help_text='0.0 ~ 1.0', null=True, verbose_name='신뢰도')),
                        ('analyzed_at', models.DateTimeField(blank=True, null=True, verbose_name='분석 완료 시각')),
                        ('error_msg', models.TextField(blank=True, verbose_name='오류 메시지')),
                        ('review', models.OneToOneField(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='sentiment',
                            to='interactions.review',
                            verbose_name='리뷰',
                        )),
                    ],
                    options={
                        'verbose_name': '감성 분석 결과',
                        'verbose_name_plural': '감성 분석 결과',
                        'db_table': 'sentiment_result',
                    },
                ),
            ],
            database_operations=[],  # 테이블 이미 존재 — DB 작업 없음
        ),
    ]
