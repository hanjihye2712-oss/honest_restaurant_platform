from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from honest_restaurant.models import PublicRestaurantData
from .models import MarketingPost
from .serializers import GenerateRequestSerializer, MarketingPostSerializer, PublishRequestSerializer


class MarketingPostViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    GET    /api/marketing/posts/               — 목록
    GET    /api/marketing/posts/<pk>/          — 단건
    PATCH  /api/marketing/posts/<pk>/          — 수정
    DELETE /api/marketing/posts/<pk>/          — 삭제
    POST   /api/marketing/posts/generate/      — AI 글 생성
    POST   /api/marketing/posts/<pk>/publish/  — 발행 (즉시/예약)
    """
    serializer_class   = MarketingPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MarketingPost.objects.filter(owner=self.request.user)

        restaurant_id = self.request.query_params.get('restaurant_id')
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        platform = self.request.query_params.get('platform')
        if platform:
            qs = qs.filter(platform=platform)

        return qs

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == 'published':
            return Response({'detail': '이미 발행된 글은 수정할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """키워드/문장 → AI 글 생성 → draft 상태로 저장"""
        serializer = GenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            restaurant = PublicRestaurantData.objects.get(pk=data['restaurant_id'])
        except PublicRestaurantData.DoesNotExist:
            return Response({'detail': '식당을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # TODO: FastAPI AI 게이트웨이 httpx 호출로 교체
        generated = self._call_ai_gateway(restaurant, data['input_prompt'], data['platform'])

        post = MarketingPost.objects.create(
            owner=request.user,
            restaurant=restaurant,
            input_prompt=data['input_prompt'],
            generated_content=generated['content'],
            final_content=generated['content'],
            hashtags=generated['hashtags'],
            platform=data['platform'],
            status='draft',
        )

        return Response(MarketingPostSerializer(post).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """즉시발행 또는 예약발행"""
        post = self.get_object()

        if post.status == 'published':
            return Response({'detail': '이미 발행된 글입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PublishRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheduled_at = serializer.validated_data.get('scheduled_at')

        if scheduled_at:
            post.scheduled_at = scheduled_at
            post.status = 'scheduled'
            post.save(update_fields=['scheduled_at', 'status', 'updated_at'])
            return Response({
                'detail': f"{scheduled_at.strftime('%Y-%m-%d %H:%M')} 예약 완료",
                'post': MarketingPostSerializer(post).data,
            })

        # 즉시 발행 — TODO: SNS API 호출로 교체
        post.status = 'published'
        post.published_at = timezone.now()
        post.save(update_fields=['status', 'published_at', 'updated_at'])
        return Response({
            'detail': '발행 완료',
            'post': MarketingPostSerializer(post).data,
        })

    def _call_ai_gateway(self, restaurant, input_prompt, platform):
        """FastAPI AI 게이트웨이 호출 자리 (추후 httpx로 교체)"""
        return {
            'content': f"[AI 생성 예정] {restaurant.name} — {input_prompt}",
            'hashtags': [f'#{restaurant.district}맛집', '#정직식당'],
        }


class MarketingManagePageView(LoginRequiredMixin, TemplateView):
    """GET /marketing/manage/ — 마케팅 글 관리 페이지"""
    template_name = 'marketing/marketing_manage.html'
    login_url     = '/accounts/login/'
