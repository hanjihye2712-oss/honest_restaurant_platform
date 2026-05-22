from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_GUEST = 'guest'
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_GUEST, '손님'),
        (ROLE_OWNER, '사장님'),
        (ROLE_ADMIN, '관리자'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_GUEST
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_owner_or_admin(self):
        return self.role in (self.ROLE_OWNER, self.ROLE_ADMIN)


class UserTrustScore(models.Model):
    """가짜 리뷰 탐지 시 패널티를 누적하는 신뢰 점수."""
    INITIAL_SCORE = 100
    # 패널티 값은 FakeReviewResult.PENALTY_FAKE가 단일 출처(source of truth)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="trust_score",
    )
    score      = models.IntegerField(default=INITIAL_SCORE, verbose_name="신뢰 점수")
    fake_count = models.IntegerField(default=0, verbose_name="가짜 리뷰 누적 횟수")

    def __str__(self):
        return f"{self.user.username} — 점수: {self.score} / 가짜: {self.fake_count}건"

    class Meta:
        db_table     = "user_trust_score"
        verbose_name = "사용자 신뢰 점수"
        verbose_name_plural = "사용자 신뢰 점수"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserTrustScore.objects.get_or_create(user=instance)