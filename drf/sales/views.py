"""
sales.views
===========
레이어 구분

    CheckoutView                — 결제 페이지 렌더링 (TemplateView)
    SuccessView                 — Toss 승인 요청 + DB 저장 (View)
    FailView                    — 결제 실패 페이지 렌더링 (TemplateView)
    CreateOrderAPIView          — 결제 전 주문 미리 저장 (View)
    TossWebhookView             — Toss 웹훅 수신 (View)
    SalesDashboardAPIView       — 대시보드용 매출 집계 JSON API (View)
    RegisterManagedRestaurantView — 식당 상세에서 관리 매장 등록 API (View)
"""
import base64
import json
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.db.models import F, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from honest_restaurant.models import PublicRestaurantData

from .models import ManagedRestaurant, SaleItem, SaleRecord

_TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"


def _managed_admin_url(pk: int) -> str:
    return f"/admin/sales/managedrestaurant/{pk}/change/"


# ══════════════════════════════════════════════════════════════
# 결제 페이지
# ══════════════════════════════════════════════════════════════

class CheckoutView(TemplateView):
    template_name = 'sales/checkout.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['toss_client_key'] = settings.TOSS_CLIENT_KEY
        return ctx


# ══════════════════════════════════════════════════════════════
# 결제 성공 — Toss API 승인 + DB 갱신
# ══════════════════════════════════════════════════════════════

class SuccessView(View):
    def get(self, request):
        payment_key = request.GET.get('paymentKey')
        order_id    = request.GET.get('orderId')
        amount      = request.GET.get('amount')

        auth = base64.b64encode(
            f"{settings.TOSS_SECRET_KEY}:".encode()
        ).decode()

        resp = requests.post(
            _TOSS_CONFIRM_URL,
            json={'paymentKey': payment_key, 'orderId': order_id, 'amount': amount},
            headers={
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/json',
            },
        )

        if resp.status_code == 200:
            SaleRecord.objects.filter(order_id=order_id).update(status=SaleRecord.STATUS_DONE)
            return render(request, 'sales/success.html', {
                'order_id':    order_id,
                'amount':      f"{int(amount):,}",
                'payment_key': payment_key,
            })

        error = resp.json()
        return render(request, 'sales/fail.html', {
            'message': error.get('message', '결제 승인에 실패했습니다.'),
            'code':    error.get('code', ''),
        })


# ══════════════════════════════════════════════════════════════
# 결제 실패 페이지
# ══════════════════════════════════════════════════════════════

class FailView(TemplateView):
    template_name = 'sales/fail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['message'] = self.request.GET.get('message', '결제에 실패했습니다.')
        ctx['code']    = self.request.GET.get('code', '')
        return ctx


# ══════════════════════════════════════════════════════════════
# 결제 전 주문 미리 저장 API
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class CreateOrderAPIView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'status': 'error', 'message': '잘못된 요청 형식입니다.'}, status=400)

        try:
            order = SaleRecord.objects.create(
                order_id=data['orderId'],
                amount=data['amount'],
                status=SaleRecord.STATUS_READY,
            )
        except KeyError as e:
            return JsonResponse({'status': 'error', 'message': f'필수 항목 누락: {e}'}, status=400)

        for item in data.get('items', []):
            try:
                SaleItem.objects.create(
                    sale_record=order,
                    menu_name=item['name'],
                    quantity=item['qty'],
                    price=item['price'],
                )
            except KeyError:
                pass
        return JsonResponse({'status': 'success'})


# ══════════════════════════════════════════════════════════════
# Toss 웹훅 수신
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class TossWebhookView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            if data.get('eventType') == 'PAYMENT_STATUS_CHANGED':
                payload = data.get('data', {})
                if payload.get('status') == SaleRecord.STATUS_DONE:
                    SaleRecord.objects.filter(
                        order_id=payload.get('orderId')
                    ).update(status=SaleRecord.STATUS_DONE)
            return JsonResponse({'status': 'OK'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ══════════════════════════════════════════════════════════════
# 대시보드용 매출 집계 JSON API
# ══════════════════════════════════════════════════════════════

DRINK_NAMES = settings.SALES_DRINK_NAMES


class SalesDashboardAPIView(View):
    """
    GET /sales/api/dashboard/
    대시보드 차트에 필요한 매출 집계 데이터를 JSON으로 반환한다.
    소주·맥주·콜라·사이다는 '주류/음료' 그룹으로 합산한다.
    로그인한 사장님 소유 가게 기준으로 필터링한다.
    """
    def get(self, request):
        now         = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 로그인한 사장님의 가게에 연결된 ManagedRestaurant 기준으로 필터
        base_filter = {'status': SaleRecord.STATUS_DONE}
        if request.user.is_authenticated:
            base_filter['restaurant__public_restaurant__owner'] = request.user

        done_qs = SaleRecord.objects.filter(**base_filter)

        # 이번 달 매출 합계
        monthly = done_qs.filter(
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 이번 달 식사 메뉴별 판매량 Top 5 (주류/음료 제외, 내 가게 한정)
        top5_filter = {
            'sale_record__status': SaleRecord.STATUS_DONE,
            'sale_record__created_at__gte': month_start,
        }
        if request.user.is_authenticated:
            top5_filter['sale_record__restaurant__public_restaurant__owner'] = request.user
        top5 = list(
            SaleItem.objects
            .filter(**top5_filter)
            .exclude(menu_name__in=DRINK_NAMES)
            .values('menu_name')
            .annotate(total_qty=Sum('quantity'))
            .order_by('-total_qty')[:5]
        )

        # 최근 14일 일별 매출
        two_weeks_ago = now - timedelta(days=13)
        daily_sales = list(
            done_qs
            .filter(created_at__gte=two_weeks_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total=Sum('amount'))
            .order_by('day')
        )

        return JsonResponse({
            'monthly_total': monthly,
            'menu_labels':   [m['menu_name'] for m in top5],
            'menu_data':     [m['total_qty'] for m in top5],
            'menu_keys':     [m['menu_name'] for m in top5],
            'daily_labels':  [str(d['day']) for d in daily_sales],
            'daily_data':    [d['total'] for d in daily_sales],
        })


# ══════════════════════════════════════════════════════════════
# 매출 상세보기 페이지
# ══════════════════════════════════════════════════════════════

class SalesDetailView(TemplateView):
    """
    GET /sales/detail/<slug>/
    slug = 메뉴명 또는 'drink' (주류/음료 그룹)
    """
    template_name = 'sales/dashboard_detail.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug', 'all')

        now         = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_label = f"{now.year}년 {now.month}월"
        month_key   = str(month_start)[:7]

        # 전달 시작점
        if month_start.month == 1:
            prev_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            prev_start = month_start.replace(month=month_start.month - 1)

        all_items  = SaleItem.objects.filter(sale_record__status=SaleRecord.STATUS_DONE)
        this_month = all_items.filter(sale_record__created_at__gte=month_start)
        prev_month = all_items.filter(
            sale_record__created_at__gte=prev_start,
            sale_record__created_at__lt=month_start,
        )

        if slug in ('all', 'drink'):
            title    = '전체 매출 상세'
            full_qs  = all_items
            cur_qs   = this_month
            prv_qs   = prev_month
        else:
            title    = slug
            full_qs  = all_items.filter(menu_name=slug)
            cur_qs   = this_month.filter(menu_name=slug)
            prv_qs   = prev_month.filter(menu_name=slug)

        def rev(qs):
            return qs.aggregate(t=Sum(F('price') * F('quantity')))['t'] or 0

        this_rev = rev(cur_qs)
        prev_rev = rev(prv_qs)

        # 전달 대비 증감
        if prev_rev:
            diff    = this_rev - prev_rev
            pct     = round(diff / prev_rev * 100, 1)
            sign    = '+' if diff >= 0 else ''
            arrow   = '↑' if diff >= 0 else '↓'
            change_str = f"{arrow} {sign}{pct}%"
            change_up  = diff >= 0
        else:
            change_str = None
            change_up  = None

        # 전체 월별 메뉴 데이터 (네비게이션용)
        monthly_menu_raw = {}
        for row in (
            full_qs
            .annotate(month=TruncMonth('sale_record__created_at'))
            .values('month', 'menu_name')
            .annotate(
                total_qty=Sum('quantity'),
                total_rev=Sum(F('price') * F('quantity')),
            )
            .order_by('month', '-total_qty')
        ):
            key = str(row['month'])[:7]
            monthly_menu_raw.setdefault(key, []).append({
                'name': row['menu_name'],
                'qty':  row['total_qty'] or 0,
                'rev':  row['total_rev'] or 0,
            })

        # 전체 월별 매출
        all_monthly_rev = list(
            full_qs
            .annotate(month=TruncMonth('sale_record__created_at'))
            .values('month')
            .annotate(total_rev=Sum(F('price') * F('quantity')))
            .order_by('month')
        )

        rev_by_year: dict[str, list] = {}
        for m in all_monthly_rev:
            year = str(m['month'])[:4]
            rev_by_year.setdefault(year, []).append({
                'month': str(m['month'])[:7],
                'rev':   m['total_rev'] or 0,
            })

        chart_labels = [str(m['month'])[:7] for m in all_monthly_rev]
        chart_data   = [m['total_rev'] or 0 for m in all_monthly_rev]

        ctx.update({
            'title':               title,
            'slug':                slug,
            'month_label':         month_label,
            'total_rev':           f"{this_rev:,}",
            'change_str':          change_str,
            'change_up':           change_up,
            'monthly_menu_json':   json.dumps(monthly_menu_raw, ensure_ascii=False),
            'current_month_key':   month_key,
            'rev_by_year_json':    json.dumps(rev_by_year, ensure_ascii=False),
            'chart_labels_json':   json.dumps(chart_labels, ensure_ascii=False),
            'chart_data_json':     json.dumps(chart_data, ensure_ascii=False),
        })
        return ctx


# ══════════════════════════════════════════════════════════════
# 식당 상세 페이지 → 관리 매장 등록 API
# ══════════════════════════════════════════════════════════════

class RegisterManagedRestaurantView(View):
    """
    POST /sales/api/register-restaurant/<pk>/
    PublicRestaurantData.pk를 받아 ManagedRestaurant 생성.
    관리자(is_staff)만 사용 가능.
    """
    def post(self, request, pk):
        if not request.user.is_staff:
            return JsonResponse({'error': '관리자만 사용 가능합니다.'}, status=403)

        try:
            pub = PublicRestaurantData.objects.get(pk=pk)
        except PublicRestaurantData.DoesNotExist:
            return JsonResponse({'error': '존재하지 않는 가게입니다.'}, status=404)

        # 이미 등록된 경우
        if hasattr(pub, 'managed'):
            m = pub.managed
            return JsonResponse({
                'status':    'already',
                'message':   '이미 관리 매장으로 등록되어 있습니다.',
                'admin_url': _managed_admin_url(m.pk),
            })

        # 공공 데이터에서 자동 입력
        m = ManagedRestaurant.objects.create(
            public_restaurant=pub,
            name=pub.name,
            address=pub.address_road or pub.address_jibun or '',
            business_type=pub.business_type or '',
            status=ManagedRestaurant.STATUS_PENDING,
            joined_at=timezone.now().date(),
        )
        return JsonResponse({
            'status':    'created',
            'message':   f'"{pub.name}" 관리 매장으로 등록됐습니다. 어드민에서 사장님 정보를 추가해주세요.',
            'admin_url': _managed_admin_url(m.pk),
        })
