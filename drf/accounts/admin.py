from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, UserTrustScore


class UserProfileInline(admin.StackedInline):
    model      = UserProfile
    can_delete = False
    verbose_name = '역할'
    fields = ('role',)


class UserTrustScoreInline(admin.StackedInline):
    model          = UserTrustScore
    can_delete     = False
    verbose_name   = '신뢰 점수'
    readonly_fields = ('score', 'fake_count')
    fields          = ('score', 'fake_count')


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserTrustScoreInline)


@admin.register(UserTrustScore)
class UserTrustScoreAdmin(admin.ModelAdmin):
    list_display  = ['user', 'score', 'fake_count']
    search_fields = ['user__username']
    ordering      = ['score']
    readonly_fields = ['user', 'score', 'fake_count']


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
