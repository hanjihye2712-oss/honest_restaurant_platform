"""
management.views
================
레이어 구분
    AdminRequiredMixin    — 관리자(role=admin) 전용 접근 제한
    DashboardView         — 운영 현황 메인 대시보드  GET /management/
    RestaurantManageView  — 식당 관리              GET /management/restaurants/
    UserManageView        — 회원 관리              GET /management/users/
    ReceiptManageView     — 영수증 인증            GET /management/receipts/
    AIManageView          — AI 분석               GET /management/ai/
    MarketingManageView   — 마케팅                GET /management/marketing/
"""

import hashlib

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from honest_restaurant.pagination import CachedPaginator, page_range
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

User = get_user_model()


# ── 공통 Mixin ────────────────────────────────────────────────
class AdminRequiredMixin:
    """role=admin 계정만 허용. 그 외는 메인으로 리다이렉트."""

    def dispatch(self, request, *args, **kwargs):
        try:
            role = request.user.profile.role
        except Exception:
            role = ''
        if role != 'admin':
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)


# ── 운영 현황 대시보드 ────────────────────────────────────────
class DashboardView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """GET /management/"""

    template_name = 'management/dashboard.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        from honest_restaurant.models import (
            PublicRestaurantData, RestaurantOwnerApplication, ReceiptVerification,
        )
        from marketing.models import MarketingPost
        from ai.ai_report.models import RestaurantAIReport
        from ai.ai_fake_review.models import FakeReviewResult
        from ai.ai_review_classifier.models import ReviewClassificationResult, RestaurantAIProfile
        from interactions.models import Review

        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        d7  = now - timezone.timedelta(days=7)
        d30 = now - timezone.timedelta(days=30)

        daily_signups = (
            User.objects
            .filter(date_joined__gte=d7)
            .annotate(day=TruncDate('date_joined'))
            .values('day')
            .annotate(cnt=Count('id'))
            .order_by('day')
        )

        ctx.update({
            'active_menu': 'dashboard',
            # 회원
            'total_users':    User.objects.count(),
            'owner_count':    User.objects.filter(profile__role='owner').count(),
            'guest_count':    User.objects.filter(profile__role='guest').count(),
            'new_users_7d':   User.objects.filter(date_joined__gte=d7).count(),
            'new_users_30d':  User.objects.filter(date_joined__gte=d30).count(),
            'signup_labels':  [str(r['day']) for r in daily_signups],
            'signup_data':    [r['cnt'] for r in daily_signups],
            'd7':             d7,
            # 식당
            'total_restaurants':  PublicRestaurantData.objects.count(),
            'linked_restaurants': PublicRestaurantData.objects.filter(owner__isnull=False).count(),
            'sns_restaurants':    PublicRestaurantData.objects.filter(sns_connected=True).count(),
            # 소유 신청
            'pending_applications':  RestaurantOwnerApplication.objects.filter(status='pending').count(),
            'approved_applications': RestaurantOwnerApplication.objects.filter(status='approved').count(),
            'rejected_applications': RestaurantOwnerApplication.objects.filter(status='rejected').count(),
            'recent_applications':   RestaurantOwnerApplication.objects.select_related('user','restaurant').order_by('-applied_at')[:8],
            # 리뷰
            'total_reviews':  Review.objects.count(),
            'reviews_7d':     Review.objects.filter(created_at__gte=d7).count(),
            'recent_reviews': Review.objects.select_related('user','restaurant').order_by('-created_at')[:8],
            # 허위 리뷰
            'fake_total':   FakeReviewResult.objects.count(),
            'fake_pending': FakeReviewResult.objects.filter(status='pending').count(),
            'fake_done':    FakeReviewResult.objects.filter(status='done').count(),
            'fake_failed':  FakeReviewResult.objects.filter(status='failed').count(),
            'fake_count':   FakeReviewResult.objects.filter(is_fake=True).count(),
            'recent_fakes': FakeReviewResult.objects.filter(is_fake=True).select_related('review__user','review__restaurant').order_by('-analyzed_at')[:8],
            # 리뷰 분류
            'cls_pending': ReviewClassificationResult.objects.filter(status='pending').count(),
            'cls_done':    ReviewClassificationResult.objects.filter(status='done').count(),
            'cls_failed':  ReviewClassificationResult.objects.filter(status='failed').count(),
            # 위생/골목장인
            'hygiene_alert_count': RestaurantAIProfile.objects.filter(hygiene_alert=True).count(),
            'hygiene_alert_list':  RestaurantAIProfile.objects.filter(hygiene_alert=True).select_related('restaurant').order_by('-recent_hygiene_negative_ratio')[:6],
            'alley_total':         RestaurantAIProfile.objects.filter(is_alley_eligible=True).count(),
            # AI 레벨 분포
            'score_lv': {
                'lv1': RestaurantAIProfile.objects.filter(ai_net_score__lt=0).count(),
                'lv2': RestaurantAIProfile.objects.filter(ai_net_score__gte=0,  ai_net_score__lt=30).count(),
                'lv3': RestaurantAIProfile.objects.filter(ai_net_score__gte=30, ai_net_score__lt=60).count(),
                'lv4': RestaurantAIProfile.objects.filter(ai_net_score__gte=60).count(),
            },
            # AI 리포트
            'report_done':    RestaurantAIReport.objects.filter(status='done').count(),
            'report_pending': RestaurantAIReport.objects.filter(status='pending').count(),
            'report_failed':  RestaurantAIReport.objects.filter(status='failed').count(),
            'recent_reports': RestaurantAIReport.objects.select_related('restaurant').order_by('-period_end')[:6],
            # 마케팅
            'mkt_total':     MarketingPost.objects.count(),
            'mkt_draft':     MarketingPost.objects.filter(status='draft').count(),
            'mkt_published': MarketingPost.objects.filter(status='published').count(),
            'mkt_scheduled': MarketingPost.objects.filter(status='scheduled').count(),
            'mkt_7d':        MarketingPost.objects.filter(created_at__gte=d7).count(),
            'recent_posts':  MarketingPost.objects.select_related('restaurant').order_by('-created_at')[:6],
            # 영수증
            'receipt_pending':  ReceiptVerification.objects.filter(status='pending').count(),
            'receipt_approved': ReceiptVerification.objects.filter(status='approved').count(),
            'receipt_rejected': ReceiptVerification.objects.filter(status='rejected').count(),
            'receipt_total':    ReceiptVerification.objects.count(),
            'recent_receipts':  ReceiptVerification.objects.select_related('user','restaurant').order_by('-submitted_at')[:8],
        })
        return ctx


# ── 식당 관리 ─────────────────────────────────────────────────
class RestaurantManageView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """GET /management/restaurants/"""

    template_name = 'management/restaurants.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        from honest_restaurant.models import PublicRestaurantData
        from ai.ai_review_classifier.models import RestaurantAIProfile

        ctx    = super().get_context_data(**kwargs)
        owner  = self.request.GET.get('owner', 'all')   # all | linked | unlinked
        search = self.request.GET.get('q', '').strip()

        base_qs = (
            PublicRestaurantData.objects
            .filter(status_code=PublicRestaurantData.STATUS_OPEN)
            .select_related('owner', 'ai_profile')
        )

        qs = base_qs
        if owner == 'linked':
            qs = qs.filter(owner__isnull=False)
        elif owner == 'unlinked':
            qs = qs.filter(owner__isnull=True)
        if search:
            qs = qs.filter(name__icontains=search)

        qs = qs.order_by('-synced_at')

        cache_key = 'mgmt_rest_' + hashlib.md5(f'{owner}|{search}'.encode()).hexdigest()[:10]
        paginator = CachedPaginator(qs, 15, cache_key=cache_key, cache_ttl=120)
        page_num  = self.request.GET.get('page', 1)
        page_obj  = paginator.get_page(page_num)

        ctx.update({
            'active_menu':    'restaurants',
            'total':          base_qs.count(),
            'linked':         base_qs.filter(owner__isnull=False).count(),
            'sns':            base_qs.filter(sns_connected=True).count(),
            'hygiene_alert':  RestaurantAIProfile.objects.filter(hygiene_alert=True).count(),
            'alley':          RestaurantAIProfile.objects.filter(is_alley_eligible=True).count(),
            'restaurants':    page_obj,
            'page_obj':       page_obj,
            'page_nums':      page_range(paginator, page_obj.number),
            'current_owner':  owner,
            'current_search': search,
        })
        return ctx


# ── 회원 관리 ─────────────────────────────────────────────────
class UserManageView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """GET /management/users/"""

    template_name = 'management/users.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx    = super().get_context_data(**kwargs)
        now    = timezone.now()
        d7     = now - timezone.timedelta(days=7)
        d30    = now - timezone.timedelta(days=30)
        role   = self.request.GET.get('role', 'all')   # all | owner | guest
        search = self.request.GET.get('q', '').strip()

        base_qs = (
            User.objects
            .select_related('profile')
            .annotate(
                review_count=Count('interaction_reviews', distinct=True),
                bookmark_count=Count('bookmarks', distinct=True),
            )
        )

        qs = base_qs
        if role == 'owner':
            qs = qs.filter(profile__role='owner')
        elif role == 'guest':
            qs = qs.filter(profile__role='guest')
        if search:
            qs = qs.filter(username__icontains=search)

        qs = qs.order_by('-date_joined')

        cache_key = 'mgmt_users_' + hashlib.md5(f'{role}|{search}'.encode()).hexdigest()[:10]
        paginator = CachedPaginator(qs, 15, cache_key=cache_key, cache_ttl=120)
        page_num  = self.request.GET.get('page', 1)
        page_obj  = paginator.get_page(page_num)

        ctx.update({
            'active_menu':    'users',
            'total':          base_qs.count(),
            'owner_count':    base_qs.filter(profile__role='owner').count(),
            'guest_count':    base_qs.filter(profile__role='guest').count(),
            'new_7d':         User.objects.filter(date_joined__gte=d7).count(),
            'new_30d':        User.objects.filter(date_joined__gte=d30).count(),
            'users':          page_obj,
            'page_obj':       page_obj,
            'page_nums':      page_range(paginator, page_obj.number),
            'current_role':   role,
            'current_search': search,
        })
        return ctx


# ── 영수증 인증 ───────────────────────────────────────────────
class ReceiptManageView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """GET /management/receipts/"""

    template_name = 'management/receipts.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        from honest_restaurant.models import ReceiptVerification

        ctx    = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', 'all')  # all | pending | approved | rejected
        search = self.request.GET.get('q', '').strip()

        base_qs = ReceiptVerification.objects.select_related('user', 'restaurant')

        qs = base_qs
        if status in ('pending', 'approved', 'rejected'):
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(restaurant__name__icontains=search)

        qs = qs.order_by('-submitted_at')

        cache_key = 'mgmt_recv_' + hashlib.md5(f'{status}|{search}'.encode()).hexdigest()[:10]
        paginator = CachedPaginator(qs, 15, cache_key=cache_key, cache_ttl=60)
        page_num  = self.request.GET.get('page', 1)
        page_obj  = paginator.get_page(page_num)

        ctx.update({
            'active_menu':    'receipts',
            'total':          base_qs.count(),
            'pending':        base_qs.filter(status='pending').count(),
            'approved':       base_qs.filter(status='approved').count(),
            'rejected':       base_qs.filter(status='rejected').count(),
            'receipts':       page_obj,
            'page_obj':       page_obj,
            'page_nums':      page_range(paginator, page_obj.number),
            'current_status': status,
            'current_search': search,
        })
        return ctx


# ── AI 분석 ──────────────────────────────────────────────────
class AIManageView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """GET /management/ai/"""

    template_name = 'management/ai.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        from ai.ai_fake_review.models import FakeReviewResult
        from ai.ai_review_classifier.models import ReviewClassificationResult, RestaurantAIProfile
        from ai.ai_report.models import RestaurantAIReport

        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_menu':    'ai',
            'cls_done':       ReviewClassificationResult.objects.filter(status='done').count(),
            'cls_pending':    ReviewClassificationResult.objects.filter(status='pending').count(),
            'cls_failed':     ReviewClassificationResult.objects.filter(status='failed').count(),
            'fake_count':     FakeReviewResult.objects.filter(is_fake=True).count(),
            'fake_done':      FakeReviewResult.objects.filter(status='done').count(),
            'fake_pending':   FakeReviewResult.objects.filter(status='pending').count(),
            'fake_total':     FakeReviewResult.objects.count(),
            'recent_fakes':   FakeReviewResult.objects.filter(is_fake=True).select_related('review__user','review__restaurant').order_by('-analyzed_at')[:10],
            'hygiene_list':   RestaurantAIProfile.objects.filter(hygiene_alert=True).select_related('restaurant').order_by('-recent_hygiene_negative_ratio'),
            'report_done':    RestaurantAIReport.objects.filter(status='done').count(),
            'report_pending': RestaurantAIReport.objects.filter(status='pending').count(),
            'report_failed':  RestaurantAIReport.objects.filter(status='failed').count(),
            'recent_reports': RestaurantAIReport.objects.select_related('restaurant').order_by('-period_end')[:10],
        })
        return ctx


# ── 마케팅 ───────────────────────────────────────────────────
class MarketingManageView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """GET /management/marketing/"""

    template_name = 'management/marketing.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        from marketing.models import MarketingPost

        ctx    = super().get_context_data(**kwargs)
        now    = timezone.now()
        d7     = now - timezone.timedelta(days=7)
        status = self.request.GET.get('status', 'all')  # all | published | scheduled | draft

        base_qs = MarketingPost.objects.select_related('restaurant')

        qs = base_qs
        if status in ('published', 'scheduled', 'draft'):
            qs = qs.filter(status=status)

        qs = qs.order_by('-created_at')

        cache_key = 'mgmt_mkt_' + hashlib.md5(status.encode()).hexdigest()[:10]
        paginator = CachedPaginator(qs, 15, cache_key=cache_key, cache_ttl=120)
        page_num  = self.request.GET.get('page', 1)
        page_obj  = paginator.get_page(page_num)

        ctx.update({
            'active_menu':    'marketing',
            'published':      base_qs.filter(status='published').count(),
            'scheduled':      base_qs.filter(status='scheduled').count(),
            'draft':          base_qs.filter(status='draft').count(),
            'week':           base_qs.filter(created_at__gte=d7).count(),
            'posts':          page_obj,
            'page_obj':       page_obj,
            'page_nums':      page_range(paginator, page_obj.number),
            'current_status': status,
        })
        return ctx
