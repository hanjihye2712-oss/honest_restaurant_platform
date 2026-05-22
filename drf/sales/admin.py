import json
from datetime import timedelta

from django.contrib import admin
from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import ExtractHour, TruncDate, TruncMonth, TruncWeek
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from marketing.models import MarketingPost

from .models import ConsultingRecord, ManagedRestaurant, SaleItem, SaleRecord


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(SaleRecord)
class SaleRecordAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'get_menu_list', 'get_amount_display', 'created_at', 'status')
    inlines = [SaleItemInline]

    def get_menu_list(self, obj):
        return ", ".join([f"{i.menu_name}({i.quantity})" for i in obj.items.all()]) or "-"
    get_menu_list.short_description = "메뉴 요약"

    def get_amount_display(self, obj):
        return f"{obj.amount:,}원"
    get_amount_display.short_description = "총 결제금액"
    get_amount_display.admin_order_field = "amount"

    # ── 어드민 상단 버튼 ──────────────────────────────
    change_list_template = "admin/sales/salerecord/change_list.html"

    # ── 커스텀 URL 추가 ──────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view),
                 name='sales_dashboard'),
        ]
        return custom + urls

    def dashboard_view(self, request):
        done_qs = SaleRecord.objects.filter(status='DONE')
        now = timezone.now()

        # ── 일별 매출 (최근 30일) ─────────────────────
        daily = list(
            done_qs
            .filter(created_at__gte=now - timedelta(days=29))
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total=Sum('amount'), cnt=Count('id'))
            .order_by('day')
        )

        # ── 주별 매출 (최근 12주) ─────────────────────
        weekly = list(
            done_qs
            .filter(created_at__gte=now - timedelta(weeks=12))
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(total=Sum('amount'), cnt=Count('id'))
            .order_by('week')
        )

        # ── 월별 매출 (전체) ──────────────────────────
        monthly = list(
            done_qs
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('amount'), cnt=Count('id'))
            .order_by('month')
        )

        # ── 요일별 평균 매출 ──────────────────────────
        DOW = ['월', '화', '수', '목', '금', '토', '일']
        dow_raw = {d: [] for d in range(7)}
        for r in done_qs.values('created_at', 'amount'):
            dow_raw[r['created_at'].weekday()].append(r['amount'])
        dow_avg = [
            {'label': DOW[d], 'avg': int(sum(v) / len(v)) if v else 0}
            for d, v in dow_raw.items()
        ]

        # ── 메뉴별 판매량 Top 10 ──────────────────────
        top_menus = list(
            SaleItem.objects
            .filter(sale_record__status='DONE')
            .values('menu_name')
            .annotate(qty=Sum('quantity'), rev=Sum(F('price') * F('quantity')))
            .order_by('-qty')[:10]
        )

        # ── KPI ───────────────────────────────────────
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_rev = done_qs.filter(created_at__gte=month_start).aggregate(t=Sum('amount'))['t'] or 0
        today_rev = done_qs.filter(created_at__date=now.date()).aggregate(t=Sum('amount'))['t'] or 0
        total_cnt = done_qs.count()

        # ── 이상 감지: 이번 주 vs 전주 ───────────────
        this_week_start = now - timedelta(days=now.weekday())
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_week_start = this_week_start - timedelta(weeks=1)

        this_week_rev = done_qs.filter(created_at__gte=this_week_start).aggregate(t=Sum('amount'))['t'] or 0
        prev_week_rev = done_qs.filter(
            created_at__gte=prev_week_start,
            created_at__lt=this_week_start
        ).aggregate(t=Sum('amount'))['t'] or 0

        if prev_week_rev:
            week_change = round((this_week_rev - prev_week_rev) / prev_week_rev * 100, 1)
        else:
            week_change = None

        # ── 시간대별 매출 (11~22시) ───────────────────
        hourly = list(
            done_qs
            .annotate(hour=ExtractHour('created_at'))
            .values('hour')
            .annotate(total=Sum('amount'), cnt=Count('id'))
            .order_by('hour')
        )

        # ── 마케팅 효과 ───────────────────────────────
        mkt_effect = []
        for post in MarketingPost.objects.filter(
            status='published', published_at__isnull=False
        ).order_by('-published_at')[:5]:
            pub_date = post.published_at
            before = done_qs.filter(
                created_at__gte=pub_date - timedelta(days=3),
                created_at__lt=pub_date
            ).aggregate(t=Sum('amount'))['t'] or 0
            after = done_qs.filter(
                created_at__gte=pub_date,
                created_at__lt=pub_date + timedelta(days=3)
            ).aggregate(t=Sum('amount'))['t'] or 0
            mkt_effect.append({
                'platform': post.get_platform_display(),
                'date': str(pub_date)[:10],
                'before': before,
                'after': after,
                'change': round((after - before) / before * 100, 1) if before else None,
            })

        # ── 메뉴 인사이트 ─────────────────────────────
        all_menus = list(
            SaleItem.objects.filter(sale_record__status='DONE')
            .values('menu_name')
            .annotate(qty=Sum('quantity'), rev=Sum(F('price') * F('quantity')))
            .order_by('-qty')
        )
        total_qty = sum(m['qty'] for m in all_menus)
        cum = 0
        for m in all_menus:
            cum += m['qty']
            m['pct'] = round(m['qty'] / total_qty * 100, 1) if total_qty else 0
            m['cum_pct'] = round(cum / total_qty * 100, 1) if total_qty else 0
        core_menus = [m for m in all_menus if m['cum_pct'] <= 70]
        low_menus = all_menus[-3:] if len(all_menus) >= 3 else all_menus

        # ── 관리 매장 목록 ────────────────────────────
        managed_restaurants = list(
            ManagedRestaurant.objects
            .values('id', 'name', 'owner_name', 'phone', 'business_type', 'status', 'joined_at', 'memo')
        )
        status_map = dict(ManagedRestaurant.STATUS_CHOICES)
        for r in managed_restaurants:
            r['status_display'] = status_map.get(r['status'], r['status'])
            r['joined_at'] = str(r['joined_at'])

        # ── 최근 상담 기록 ────────────────────────────
        recent_consulting = list(
            ConsultingRecord.objects.select_related('created_by')
            .order_by('-date')[:5]
            .values(
                'date', 'category', 'content', 'next_action',
                'next_date', 'created_by__username'
            )
        )
        # category display name 변환
        cat_map = dict(ConsultingRecord.CATEGORY_CHOICES)
        for c in recent_consulting:
            c['category_display'] = cat_map.get(c['category'], c['category'])
            c['date'] = str(c['date'])
            c['next_date'] = str(c['next_date']) if c['next_date'] else ''

        ctx = {
            **self.admin_site.each_context(request),
            'title': '매출 대시보드',
            # KPI
            'kpi_month': f"{this_rev:,}",
            'kpi_today': f"{today_rev:,}",
            'kpi_total': f"{total_cnt:,}",
            # 이상 감지
            'this_week_rev': f"{this_week_rev:,}",
            'prev_week_rev': f"{prev_week_rev:,}",
            'week_change': week_change,
            # 기존 차트
            'daily_json': json.dumps(
                [{'x': str(d['day']), 'y': d['total'], 'cnt': d['cnt']} for d in daily]
            ),
            'weekly_json': json.dumps(
                [{'x': str(w['week'])[:10], 'y': w['total'], 'cnt': w['cnt']} for w in weekly]
            ),
            'monthly_json': json.dumps(
                [{'x': str(m['month'])[:7], 'y': m['total'], 'cnt': m['cnt']} for m in monthly]
            ),
            'dow_json': json.dumps(dow_avg),
            'menu_json': json.dumps(
                [{'name': m['menu_name'], 'qty': m['qty'], 'rev': m['rev']} for m in top_menus],
                ensure_ascii=False
            ),
            # 신규
            'hourly_json': json.dumps(
                [{'hour': h['hour'], 'total': h['total'], 'cnt': h['cnt']} for h in hourly]
            ),
            'mkt_effect_json': json.dumps(mkt_effect, ensure_ascii=False),
            'core_menus_json': json.dumps(
                [{'name': m['menu_name'], 'qty': m['qty'], 'rev': m['rev'],
                  'pct': m['pct'], 'cum_pct': m['cum_pct']} for m in core_menus],
                ensure_ascii=False
            ),
            'low_menus_json': json.dumps(
                [{'name': m['menu_name'], 'qty': m['qty'], 'rev': m['rev'],
                  'pct': m['pct']} for m in low_menus],
                ensure_ascii=False
            ),
            'consulting_json':   json.dumps(recent_consulting, ensure_ascii=False),
            'restaurants_json':  json.dumps(managed_restaurants, ensure_ascii=False),
            'restaurant_count':  len(managed_restaurants),
        }
        return render(request, 'admin/sales/salerecord/dashboard.html', ctx)


@admin.register(ConsultingRecord)
class ConsultingRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'category', 'content_preview', 'next_action', 'next_date', 'created_by')
    list_filter = ('category', 'date')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '내용'


@admin.register(ManagedRestaurant)
class ManagedRestaurantAdmin(admin.ModelAdmin):
    list_display  = ('name', 'owner_name', 'phone', 'business_type', 'status', 'joined_at', 'dashboard_link')
    list_filter   = ('status', 'business_type')
    search_fields = ('name', 'owner_name', 'phone')
    ordering      = ('-joined_at',)

    def dashboard_link(self, obj):
        return format_html(
            '<a href="{}/dashboard/" style="background:#1a2744;color:#fff;padding:4px 12px;'
            'border-radius:3px;font-size:12px;text-decoration:none;">📊 대시보드</a>',
            obj.pk
        )
    dashboard_link.short_description = '대시보드'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/dashboard/',
                 self.admin_site.admin_view(self.restaurant_dashboard_view),
                 name='managed_restaurant_dashboard'),
        ]
        return custom + urls

    def restaurant_dashboard_view(self, request, pk):
        restaurant = ManagedRestaurant.objects.get(pk=pk)
        done_qs    = SaleRecord.objects.filter(status='DONE', restaurant=restaurant)
        now        = timezone.now()

        # 일별 (최근 30일)
        daily = list(
            done_qs.filter(created_at__gte=now - timedelta(days=29))
            .annotate(day=TruncDate('created_at'))
            .values('day').annotate(total=Sum('amount'), cnt=Count('id')).order_by('day')
        )
        # 월별
        monthly = list(
            done_qs.annotate(month=TruncMonth('created_at'))
            .values('month').annotate(total=Sum('amount'), cnt=Count('id')).order_by('month')
        )
        # 요일별 평균
        DOW = ['월', '화', '수', '목', '금', '토', '일']
        dow_raw = {d: [] for d in range(7)}
        for r in done_qs.values('created_at', 'amount'):
            dow_raw[r['created_at'].weekday()].append(r['amount'])
        dow_avg = [{'label': DOW[d], 'avg': int(sum(v)/len(v)) if v else 0} for d, v in dow_raw.items()]

        # 시간대별
        hourly = list(
            done_qs.annotate(hour=ExtractHour('created_at'))
            .values('hour').annotate(total=Sum('amount'), cnt=Count('id')).order_by('hour')
        )
        # 메뉴 Top 10
        top_menus = list(
            SaleItem.objects.filter(sale_record__status='DONE', sale_record__restaurant=restaurant)
            .values('menu_name').annotate(qty=Sum('quantity'), rev=Sum(F('price') * F('quantity')))
            .order_by('-qty')[:10]
        )
        # KPI
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_rev  = done_qs.filter(created_at__gte=month_start).aggregate(t=Sum('amount'))['t'] or 0
        today_rev = done_qs.filter(created_at__date=now.date()).aggregate(t=Sum('amount'))['t'] or 0
        total_cnt = done_qs.count()

        # 이번 주 vs 전주
        this_week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        prev_week_start = this_week_start - timedelta(weeks=1)
        this_week_rev = done_qs.filter(created_at__gte=this_week_start).aggregate(t=Sum('amount'))['t'] or 0
        prev_week_rev = done_qs.filter(created_at__gte=prev_week_start, created_at__lt=this_week_start).aggregate(t=Sum('amount'))['t'] or 0
        week_change = round((this_week_rev - prev_week_rev) / prev_week_rev * 100, 1) if prev_week_rev else None

        ctx = {
            **self.admin_site.each_context(request),
            'title':          f'{restaurant.name} — 매출 대시보드',
            'restaurant':     restaurant,
            'kpi_month':      f"{this_rev:,}",
            'kpi_today':      f"{today_rev:,}",
            'kpi_total':      f"{total_cnt:,}",
            'this_week_rev':  f"{this_week_rev:,}",
            'prev_week_rev':  f"{prev_week_rev:,}",
            'week_change':    week_change,
            'daily_json':     json.dumps([{'x': str(d['day']), 'y': d['total'], 'cnt': d['cnt']} for d in daily]),
            'weekly_json':    json.dumps([]),
            'monthly_json':   json.dumps([{'x': str(m['month'])[:7], 'y': m['total'], 'cnt': m['cnt']} for m in monthly]),
            'dow_json':       json.dumps(dow_avg),
            'hourly_json':    json.dumps([{'hour': h['hour'], 'total': h['total']} for h in hourly]),
            'menu_json':      json.dumps([{'name': m['menu_name'], 'qty': m['qty'], 'rev': m['rev']} for m in top_menus], ensure_ascii=False),
            'mkt_effect_json':   json.dumps([]),
            'core_menus_json':   json.dumps([]),
            'low_menus_json':    json.dumps([]),
            'consulting_json':   json.dumps([]),
            'restaurants_json':  json.dumps([]),
            'restaurant_count':  0,
        }
        return render(request, 'admin/sales/salerecord/dashboard.html', ctx)
