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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_GUEST)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_owner_or_admin(self):
        return self.role in (self.ROLE_OWNER, self.ROLE_ADMIN)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
