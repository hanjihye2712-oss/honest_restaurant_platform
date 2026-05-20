from django.db import models
from django.contrib.auth.models import User
from honest_restaurant.models import PublicRestaurantData


class MarketingPost(models.Model):

    PLATFORM_CHOICES = [
        ('instagram',   'Instagram'),
        ('facebook',    'Facebook'),
        ('naver_blog',  '네이버 블로그'),
        ('kakao_story', '카카오스토리'),
    ]

    STATUS_CHOICES = [
        ('draft',     '임시저장'),
        ('scheduled', '예약발행'),
        ('published', '발행완료'),
        ('failed',    '발행실패'),
    ]

    owner      = models.ForeignKey(User,                 on_delete=models.CASCADE, related_name='marketing_posts')
    restaurant = models.ForeignKey(PublicRestaurantData, on_delete=models.CASCADE, related_name='marketing_posts')

    input_prompt      = models.TextField(verbose_name='사장님 입력 키워드/문장')
    generated_content = models.TextField(verbose_name='AI 생성 원본')
    final_content     = models.TextField(verbose_name='최종 발행 내용')
    hashtags          = models.JSONField(default=list, verbose_name='해시태그 목록')

    platform         = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='발행 플랫폼')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    scheduled_at     = models.DateTimeField(null=True, blank=True, verbose_name='예약 발행 시각')
    published_at     = models.DateTimeField(null=True, blank=True, verbose_name='실제 발행 시각')
    external_post_id = models.CharField(max_length=300, blank=True, verbose_name='SNS 게시물 ID')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketing_post'
        ordering = ['-created_at']
        verbose_name = '마케팅 게시물'

    def __str__(self):
        return f"[{self.get_platform_display()}] {self.restaurant.name} — {self.get_status_display()}"
