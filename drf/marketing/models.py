from django.db import models
from django.contrib.auth.models import User
from honest_restaurant.models import PublicRestaurantData


class MarketingPlatformConfig(models.Model):
    """플랫폼별 작성 가이드 — 어드민에서 관리"""
    platform     = models.CharField(max_length=20, unique=True, verbose_name='플랫폼 ID')
    display_name = models.CharField(max_length=50, verbose_name='표시명')
    guide        = models.TextField(verbose_name='작성 가이드')
    is_active    = models.BooleanField(default=True, verbose_name='활성화')
    order        = models.PositiveSmallIntegerField(default=0, verbose_name='순서')

    class Meta:
        db_table = 'marketing_platform_config'
        ordering = ['order', 'platform']
        verbose_name = '플랫폼 설정'
        verbose_name_plural = '플랫폼 설정'

    def __str__(self):
        status = '활성' if self.is_active else '비활성'
        return f"{self.display_name} ({status})"


class MarketingAIConfig(models.Model):
    """AI 글 생성 설정 싱글턴 — 어드민에서 관리 (레코드 1개만 사용)"""
    model_name          = models.CharField(max_length=100, default='gemini-2.5-flash', verbose_name='AI 모델명')
    temperature         = models.FloatField(default=1.0, verbose_name='Temperature (0.0 ~ 2.0)')
    role_description    = models.TextField(verbose_name='AI 역할 설명')
    writing_instruction = models.TextField(verbose_name='글쓰기 지시사항')

    class Meta:
        db_table = 'marketing_ai_config'
        verbose_name = 'AI 글 생성 설정'
        verbose_name_plural = 'AI 글 생성 설정'

    def __str__(self):
        return f"AI 설정 (모델: {self.model_name})"

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'role_description': '당신은 동네 식당 사장님의 SNS 마케팅을 돕는 전문가입니다.',
                'writing_instruction': (
                    '위 정보를 바탕으로 {platform}에 올릴 마케팅 글을 작성해주세요.\n'
                    '오늘의 날씨나 기념일이 있다면 자연스럽게 녹여주세요.\n'
                    '광고처럼 보이지 않고 진심이 담긴 글로 써주세요.'
                ),
            }
        )
        return config


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
