from django.db import models

_DEFAULT_ROLE = "당신은 식당 사장님에게 운영 인사이트를 전달하는 친절한 AI 어시스턴트입니다.\n아래 최근 {period_days}일 고객 리뷰 분석 데이터를 바탕으로 리포트를 작성해주세요."

_DEFAULT_RULES = """1. 사장님을 "사장님"으로 호칭
2. 가장 눈에 띄는 긍정 포인트 1가지를 먼저 언급
3. 개선이 필요한 부분이 있으면 부드럽게 제안 (없으면 생략)
4. 위생 경고가 있으면 반드시 포함
5. 전체 3~4문장, 친근하고 실용적인 말투
6. 이모지 1~2개만 사용
7. 마케팅 문구나 과장 표현 금지"""


class AIReportConfig(models.Model):
    """AI 리포트 생성 설정 싱글턴 — 어드민에서 관리 (레코드 1개만 사용)"""
    model_name        = models.CharField(max_length=100, default='gemini-2.5-flash', verbose_name='AI 모델명')
    temperature       = models.FloatField(default=1.0, verbose_name='Temperature (0.0 ~ 2.0)')
    report_period_days = models.PositiveIntegerField(default=90, verbose_name='분석 기간 (일)')
    role_description  = models.TextField(verbose_name='AI 역할 설명', default=_DEFAULT_ROLE)
    writing_rules     = models.TextField(verbose_name='작성 규칙', default=_DEFAULT_RULES)

    class Meta:
        db_table            = 'ai_report_config'
        verbose_name        = 'AI 리포트 설정'
        verbose_name_plural = 'AI 리포트 설정'

    def __str__(self):
        return f"AI 리포트 설정 (모델: {self.model_name})"

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1, defaults={
            'role_description': _DEFAULT_ROLE,
            'writing_rules':    _DEFAULT_RULES,
        })
        return config


class RestaurantAIReport(models.Model):
    """
    Gemini API로 생성한 식당 AI 리포트.
    하루 1회 배치 또는 수동 트리거로 생성된다.
    """

    STATUS_PENDING = "pending"
    STATUS_DONE    = "done"
    STATUS_FAILED  = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "생성 대기"),
        (STATUS_DONE,    "생성 완료"),
        (STATUS_FAILED,  "생성 실패"),
    ]

    restaurant = models.ForeignKey(
        "honest_restaurant.PublicRestaurantData",
        on_delete=models.CASCADE,
        related_name="ai_reports",
        verbose_name="식당",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="상태",
    )

    # 생성된 리포트 본문 (3~4문장 자연어)
    report_text  = models.TextField(blank=True, verbose_name="리포트 본문")
    # 앱 푸시 알림용 요약 (2~3줄)
    push_message = models.TextField(blank=True, verbose_name="푸시 알림 메시지")

    # 리포트 집계 기준 기간
    period_start = models.DateField(verbose_name="분석 시작일")
    period_end   = models.DateField(verbose_name="분석 종료일")

    generated_at = models.DateTimeField(null=True, blank=True, verbose_name="생성 완료 시각")
    error_msg    = models.TextField(blank=True, verbose_name="오류 메시지")

    def __str__(self):
        return f"{self.restaurant.name} ({self.period_end}) — {self.get_status_display()}"

    class Meta:
        db_table            = "restaurant_ai_report"
        ordering            = ["-period_end"]
        verbose_name        = "AI 리포트"
        verbose_name_plural = "AI 리포트"
