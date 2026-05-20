from django.db import models
from django.contrib.auth.models import User


class SaleRecord(models.Model):
    restaurant = models.ForeignKey(
        'ManagedRestaurant',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sale_records',
        verbose_name='관리 매장',
    )
    order_id   = models.CharField(max_length=100, unique=True, verbose_name="주문번호")
    amount     = models.IntegerField(verbose_name="총 결제금액")
    status     = models.CharField(max_length=20, default="READY", verbose_name="결제상태")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="결제일시")

    def __str__(self):
        name = self.restaurant.name if self.restaurant else '미연결'
        return f"[{name}] {self.order_id} ({self.amount}원)"

class SaleItem(models.Model):
    # 주문번호와 연결 (주문 하나에 여러 메뉴)
    sale_record = models.ForeignKey(SaleRecord, on_delete=models.CASCADE, related_name='items')
    menu_name = models.CharField(max_length=100, verbose_name="메뉴명")
    quantity = models.IntegerField(verbose_name="수량")
    price = models.IntegerField(verbose_name="단가")

    def __str__(self):
        return f"{self.menu_name} - {self.quantity}개"


class ManagedRestaurant(models.Model):
    STATUS_CHOICES = [
        ('active',   '관리 중'),
        ('inactive', '휴면'),
        ('pending',  '검토 중'),
    ]
    public_restaurant = models.OneToOneField(
        'honest_restaurant.PublicRestaurantData',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed',
        verbose_name='공공 데이터 연결',
    )
    name          = models.CharField(max_length=100, verbose_name='상호명')
    owner_name    = models.CharField(max_length=50,  blank=True, verbose_name='사장님 성함')
    phone         = models.CharField(max_length=20,  blank=True, verbose_name='연락처')
    address       = models.CharField(max_length=200, blank=True, verbose_name='주소')
    business_type = models.CharField(max_length=50,  blank=True, verbose_name='업종')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='상태')
    joined_at     = models.DateField(verbose_name='등록일')
    memo          = models.TextField(blank=True, verbose_name='메모')

    class Meta:
        ordering = ['-joined_at']
        verbose_name = '관리 매장'
        verbose_name_plural = '관리 매장'

    def __str__(self):
        return f"{self.name} ({self.owner_name})"


class ConsultingRecord(models.Model):
    CATEGORY_CHOICES = [
        ('sales', '매출 분석'),
        ('menu', '메뉴 전략'),
        ('marketing', '마케팅'),
        ('pricing', '가격 정책'),
        ('other', '기타'),
    ]
    date = models.DateField(verbose_name='상담 일자')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='분류')
    content = models.TextField(verbose_name='상담 내용')
    next_action = models.TextField(blank=True, verbose_name='다음 액션')
    next_date = models.DateField(null=True, blank=True, verbose_name='다음 상담 예정일')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='담당자')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = '상담 기록'
        verbose_name_plural = '상담 기록'

    def __str__(self):
        return f"[{self.get_category_display()}] {self.date}"