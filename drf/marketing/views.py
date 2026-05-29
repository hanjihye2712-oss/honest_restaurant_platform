from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from honest_restaurant.models import PublicRestaurantData
from .ai_service import generate_marketing_content, get_active_platforms
from .context_service import get_today_context
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
        """키워드/문장 + 오늘의 날씨·기념일·뉴스 → Gemini AI 글 생성 → draft 저장"""
        serializer = GenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            restaurant = PublicRestaurantData.objects.get(pk=data['restaurant_id'])
        except PublicRestaurantData.DoesNotExist:
            return Response({'detail': '식당을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            context   = get_today_context()
            generated = generate_marketing_content(
                restaurant,
                data['input_prompt'],
                data['platform'],
                context,
            )
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                msg = 'AI 요청이 너무 많습니다. 잠시 후 다시 시도해주세요. (약 1분 후)'
            elif '401' in err_str or 'API_KEY' in err_str:
                msg = 'AI API 키가 유효하지 않습니다. 관리자에게 문의해주세요.'
            else:
                msg = 'AI 글 생성에 실패했습니다. 잠시 후 다시 시도해주세요.'
            return Response({'detail': msg}, status=status.HTTP_502_BAD_GATEWAY)

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


class MarketingManagePageView(LoginRequiredMixin, TemplateView):
    """GET /marketing/manage/ — 마케팅 글 관리 페이지"""
    template_name = 'marketing/marketing_manage.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        restaurant = getattr(self.request.user, 'owned_restaurant', None)
        ctx['restaurant']       = restaurant
        ctx['active_platforms'] = get_active_platforms()
        ctx['sns_connected']    = bool(restaurant and restaurant.sns_connected)
        return ctx
