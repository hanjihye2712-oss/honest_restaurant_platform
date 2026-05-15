from django.db import models


class PublicRestaurantData(models.Model):
    """
    서울시 공공데이터 - 일반음식점 인허가 정보
    출처: 서울 열린데이터광장 LOCALDATA_072404
    -----------------------------------------------
    ① 가게 식별 / 기본 정보  (검증 LV2 핵심)
    ② 정부 인증 / 위생 정보  (LV2 배지·라벨 핵심 데이터)
    ③ 위치 좌표              (지도·유동인구 분석)
    ④ 내부 관리 필드         (동기화 메타 정보)
    """

    # ─────────────────────────────────────────────
    # ① 가게 식별 / 기본 정보 — 검증 LV2 핵심
    # ─────────────────────────────────────────────

    management_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="관리번호",
        help_text="서울시 공공DB 원본 식별자 (내부용, 사용자 노출 불필요)",
    )

    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name="업소명",
        help_text="[필수] 사업자등록증 명칭과 자동 대조 → LV2 검증",
    )

    address_road = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="도로명주소",
        help_text="[필수] 지도 핀 표시 + 사장님 주소 진위 확인 (LV2)",
    )

    address_jibun = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="지번주소",
        help_text="[필수] 도로명 주소 보완용",
    )

    province = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name="시/도",
        help_text="address_road 첫 번째 토큰에서 자동 추출 (예: 서울특별시, 경기도, 부산광역시)",
    )

    district = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name="자치구/시/군",
        help_text="주소의 두 번째 단위 (구·시·군). 상권별 분석 & 지자체 B2G 리포트",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="전화번호",
        help_text="[권장] 고객 앱 연결 + 사장님 연락처 진위 확인",
    )

    business_type = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="업태구분명",
        help_text="[필수] 식당 카테고리 자동 분류 (한식/중식/분식 등) → 검색 필터 + AI 콘텐츠 생성 시 업종 컨텍스트",
    )

    category_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="업종명",
        help_text="[필수] 세부 업종명 (업태구분명의 하위 분류)",
    )

    # ─────────────────────────────────────────────
    # ② 정부 인증 / 위생 정보 — LV2 배지·라벨의 핵심 데이터
    # ─────────────────────────────────────────────

    sanitation_business_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="위생업종명",
        help_text="[필수] 식품위생법상 업종 확인 → 위생 등급 라벨 기준 / '일반음식점' 여부로 착한가격업소 신청 자격 판단",
    )

    license_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="인허가일자",
        help_text="[필수] 영업 기간 계산 → LV4 '6개월 이상 안정적 운영' 조건 / 노포 판별(10년+) → 아카이브 프로젝트 자동 추천",
    )

    # 영업상태 코드값 상수
    STATUS_OPEN = "01"
    STATUS_SUSPENDED = "02"
    STATUS_CLOSED = "03"
    STATUS_CHOICES = [
        (STATUS_OPEN, "영업"),
        (STATUS_SUSPENDED, "휴업"),
        (STATUS_CLOSED, "폐업"),
    ]

    status_code = models.CharField(
        max_length=10,
        blank=True,
        db_index=True,
        choices=STATUS_CHOICES,
        verbose_name="영업상태구분코드",
        help_text="[필수] 폐업·취소 가게 자동 감지 → 검증 배지 즉시 회수",
    )

    area = models.FloatField(
        null=True,
        blank=True,
        verbose_name="소재지면적(㎡)",
        help_text="[선택] 착한가격업소 신청 요건(면적 기준) 자동 판단 보조",
    )

    last_modified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="최종수정시점",
        help_text="[권장] 공공 DB 최신 업데이트 여부 추적 → 캐싱 전략 기준",
    )

    # ─────────────────────────────────────────────
    # ③ 위치 좌표 — 지도·유동인구 분석
    # ─────────────────────────────────────────────

    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="위도 (WGS84)",
        help_text="[필수] 고객 앱 지도에 가게 핀 표시 / 반경 1km 재고 나눔 마켓 (사장님 앱 모듈2)",
    )

    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="경도 (WGS84)",
        help_text="[필수] 고객 앱 지도에 가게 핀 표시 / 반경 1km 재고 나눔 마켓 (사장님 앱 모듈2)",
    )

    # ─────────────────────────────────────────────
    # ④ 내부 관리 필드 — 동기화 메타 정보
    # ─────────────────────────────────────────────

    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="우리 서버 동기화 시각",
        help_text="Celery beat 매일 새벽 3시 자동 갱신",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="최초 수집 시각",
    )

    # ─────────────────────────────────────────────
    # 프로퍼티 / 헬퍼
    # ─────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        """영업 중 여부 — 배지 발급 가능 조건 1번"""
        return self.status_code == self.STATUS_OPEN

    @property
    def operating_years(self) -> float | None:
        """영업 연수 계산 — LV4 조건 / 노포 판별에 사용"""
        if not self.license_date:
            return None
        from django.utils import timezone
        delta = timezone.now().date() - self.license_date
        return round(delta.days / 365.25, 1)

    @property
    def is_veteran_store(self) -> bool:
        """노포 여부 (10년 이상) — 아카이브 프로젝트 자동 추천 대상"""
        years = self.operating_years
        return years is not None and years >= 10

    def __str__(self):
        return f"[{self.province or self.district}] {self.name} ({self.get_status_code_display()})"

    class Meta:
        db_table = "public_restaurant_data"
        verbose_name = "공공 음식점 데이터"
        verbose_name_plural = "공공 음식점 데이터"
        indexes = [
            models.Index(fields=["district", "status_code"],  name="idx_district_status"),
            models.Index(fields=["latitude",  "longitude"],   name="idx_lat_lng"),
            models.Index(fields=["license_date"],             name="idx_license_date"),

            # ❶ 기본 목록: WHERE status_code='01' ORDER BY synced_at DESC
            models.Index(fields=["status_code", "synced_at"], name="idx_status_synced"),
            # ❷ 시/도 필터 + 정렬
            models.Index(fields=["province", "status_code", "synced_at"], name="idx_province_status_synced"),
            # ❸ 자치구 필터 + 정렬
            models.Index(fields=["district", "status_code", "synced_at"], name="idx_district_status_synced"),
            # ❹ 업태 필터 + 정렬
            models.Index(fields=["business_type", "status_code", "synced_at"], name="idx_biztype_status_synced"),
            # ❺ 이름 검색
            models.Index(fields=["name"], name="idx_name"),
        ]
        constraints = [
            # 도로명주소가 있는 경우: 상호명+도로명주소+업태 중복 방지
            models.UniqueConstraint(
                fields=["name", "address_road", "business_type"],
                condition=models.Q(address_road__gt=""),
                name="uq_name_road_biztype",
            ),
        ]
        ordering = ["-synced_at"]


class RestaurantMedia(models.Model):
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_CHOICES = [
        (TYPE_IMAGE, "이미지"),
        (TYPE_VIDEO, "동영상"),
    ]

    restaurant = models.ForeignKey(
        PublicRestaurantData,
        on_delete=models.CASCADE,
        related_name="media",
    )
    uploaded_by = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        verbose_name="업로더",
    )
    file = models.FileField(upload_to="restaurant_media/")
    media_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.restaurant.name} — {self.get_media_type_display()}"

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "식당 미디어"
        verbose_name_plural = "식당 미디어"


class ReceiptVerification(models.Model):
    STATUS_PENDING  = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES  = [
        (STATUS_PENDING,  "검토 중"),
        (STATUS_APPROVED, "인증 완료"),
        (STATUS_REJECTED, "인증 거부"),
    ]

    restaurant = models.ForeignKey(
        PublicRestaurantData,
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        verbose_name="신청자",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="인증 상태",
    )
    receipt_image = models.ImageField(
        upload_to="receipts/",
        verbose_name="영수증 이미지",
        blank=True,
        null=True,
    )
    comment = models.TextField(
        blank=True,
        verbose_name="한 줄 후기",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.restaurant.name} — {self.user} ({self.get_status_display()})"

    class Meta:
        unique_together = ["restaurant", "user"]
        verbose_name = "영수증 인증"
        verbose_name_plural = "영수증 인증"


