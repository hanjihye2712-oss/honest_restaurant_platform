from rest_framework import serializers
from .models import PublicRestaurantData


class PublicRestaurantDataSerializer(serializers.ModelSerializer):
    """
    서울시 공공 식당 데이터 시리얼라이저
    - 프로퍼티(is_open, operating_years, is_veteran_store)도 응답에 포함
    - management_no 는 내부용이므로 write_only 처리 (응답에 미노출)
    """

    is_open          = serializers.BooleanField(read_only=True)
    operating_years  = serializers.FloatField(read_only=True)
    is_veteran_store = serializers.BooleanField(read_only=True)

    class Meta:
        model  = PublicRestaurantData
        fields = [
            # ① 가게 식별 / 기본 정보
            "id",
            "name",
            "address_road",
            "address_jibun",
            "district",
            "phone",
            "business_type",
            "category_name",
            # ② 정부 인증 / 위생 정보
            "sanitation_business_type",
            "license_date",
            "license_cancel_date",
            "status_code",
            "area",
            "last_modified_at",
            # ③ 위치 좌표
            "latitude",
            "longitude",
            # ④ 내부 관리
            "synced_at",
            "created_at",
            # 프로퍼티
            "is_open",
            "operating_years",
            "is_veteran_store",
            # 내부 식별자 (응답 미노출)
            "management_no",
        ]
        extra_kwargs = {
            "management_no": {"write_only": True},
        }