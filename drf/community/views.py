"""
community.views
===============
소비자 참여 기능 UI — 현재는 더미 데이터로 화면만 구현.
추후 각 기능별 모델·로직 연동 예정.

    BadgeView         — 뱃지·등급   GET /community/badges/
    ChallengeView     — 월간 챌린지  GET /community/challenge/
    PriceReportView   — 가격 감시단  GET /community/price-report/
    ReviewerView      — 인증 리뷰어  GET /community/reviewer/
    MembershipView    — 구독 멤버십  GET /community/membership/
    TourView          — 탐방 투어    GET /community/tour/
    MyReportView      — 연말 리포트  GET /community/my-report/
    SocialView        — 소셜·팔로우  GET /community/social/
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class BadgeView(LoginRequiredMixin, TemplateView):
    template_name = 'community/badge.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'badges'
        ctx['earned_badges'] = [
            {'icon': '🧾', 'name': '영수증 탐험가', 'desc': '영수증 인증 5건 달성', 'date': '2026.04.12'},
            {'icon': '🍜', 'name': '맛집 발굴러',   'desc': '첫 리뷰 작성',         'date': '2026.03.28'},
            {'icon': '❤️', 'name': '찜 마니아',     'desc': '북마크 10개 달성',     'date': '2026.02.10'},
        ]
        locked_raw = [
            {'icon': '🏯', 'name': '노포 사냥꾼',  'desc': '20년 이상 노포 3곳 방문',  'progress': 1,  'total': 3},
            {'icon': '🌏', 'name': '동네 전문가',  'desc': '같은 구 5건 인증',          'progress': 3,  'total': 5},
            {'icon': '🛡️', 'name': '신뢰 수호자', 'desc': '허위 리뷰 신고 확인 완료',  'progress': 0,  'total': 1},
            {'icon': '⭐', 'name': '가격 감시단',  'desc': '가격 일치 가게 10곳 인증',  'progress': 4,  'total': 10},
            {'icon': '📸', 'name': '포토 리뷰어',  'desc': '사진 포함 리뷰 5건',        'progress': 2,  'total': 5},
            {'icon': '👑', 'name': '정직 마스터',  'desc': '모든 뱃지 달성',            'progress': 3,  'total': 11},
        ]
        for b in locked_raw:
            b['pct'] = round(b['progress'] / b['total'] * 100) if b['total'] else 0
        ctx['locked_badges'] = locked_raw
        ctx['level']      = 2
        ctx['level_name'] = '탐험가'
        ctx['level_next'] = '전문가'
        ctx['exp']        = 340
        ctx['exp_next']   = 500
        ctx['exp_pct']    = 68
        ctx['total_badge_count'] = len(ctx['earned_badges']) + len(ctx['locked_badges'])
        return ctx


class ChallengeView(LoginRequiredMixin, TemplateView):
    template_name = 'community/challenge.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'challenge'
        ctx['month'] = '2026년 5월'
        ctx['active_challenges'] = [
            {
                'title': '강남구 한식 정복', 'desc': '강남구 한식 맛집 3곳 영수증 인증',
                'reward': '동네 전문가 뱃지 + 50 포인트',
                'progress': 2, 'total': 3, 'pct': 67, 'dday': 8, 'css_class': '',
            },
            {
                'title': '냉면 시즌 탐방', 'desc': '냉면 전문점 영수증 인증 2건',
                'reward': '시즌 한정 뱃지 + 30 포인트',
                'progress': 1, 'total': 2, 'pct': 50, 'dday': 8, 'css_class': '',
            },
            {
                'title': '리뷰 작성왕', 'desc': '이번 달 리뷰 5건 작성',
                'reward': '맛집 발굴러 뱃지 + 70 포인트',
                'progress': 3, 'total': 5, 'pct': 60, 'dday': 8, 'css_class': '',
            },
        ]
        ctx['completed_challenges'] = [
            {'title': '4월 노포 탐방',   'reward': '노포 뱃지',   'date': '2026.04.30'},
            {'title': '3월 영수증 챌린지', 'reward': '탐험가 뱃지', 'date': '2026.03.31'},
        ]
        return ctx


class PriceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'community/price_report.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'price-report'
        ctx['my_reports'] = [
            {'restaurant': '신목사골칼국수', 'menu': '사골칼국수', 'reported_price': 9000, 'menu_price': 8000, 'status': 'confirmed', 'date': '2026.05.20'},
            {'restaurant': '형제육회',       'menu': '육회비빔밥', 'reported_price': 13000,'menu_price': 12000,'status': 'reviewing','date': '2026.05.15'},
            {'restaurant': '한솥도시락',     'menu': '돈까스도시락','reported_price':5500, 'menu_price': 5000, 'status': 'rejected', 'date': '2026.04.28'},
        ]
        return ctx


class ReviewerView(TemplateView):
    template_name = 'community/reviewer.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'reviewer'
        reviewers_raw = [
            {'rank': 1, 'username': 'foodlover_kim',  'reviews': 87, 'verifications': 63, 'badges': 9, 'certified': True},
            {'rank': 2, 'username': 'honest_eater',   'reviews': 72, 'verifications': 55, 'badges': 8, 'certified': True},
            {'rank': 3, 'username': 'seoul_foodie',   'reviews': 65, 'verifications': 48, 'badges': 7, 'certified': True},
            {'rank': 4, 'username': 'noodle_hunter',  'reviews': 51, 'verifications': 40, 'badges': 6, 'certified': True},
            {'rank': 5, 'username': 'bapsim_official','reviews': 48, 'verifications': 35, 'badges': 5, 'certified': True},
            {'rank': 6, 'username': 'my_account',     'reviews': 12, 'verifications': 8,  'badges': 3, 'certified': False},
        ]
        for r in reviewers_raw:
            rank_cls = f'rank-{r["rank"]}' if r['rank'] <= 3 else ''
            my_cls   = 'my-row' if r['username'] == 'my_account' else ''
            r['row_class'] = (rank_cls + ' ' + my_cls).strip()
        ctx['top_reviewers'] = reviewers_raw
        ctx['my_rank']          = 6
        ctx['requirements']     = [
            {'label': '리뷰 30건 이상',       'current': 12, 'total': 30, 'pct': 40,  'done': False},
            {'label': '영수증 인증 20건 이상', 'current': 8,  'total': 20, 'pct': 40,  'done': False},
            {'label': '허위 신고 0건',         'current': 0,  'total': 0,  'pct': 100, 'done': True},
        ]
        return ctx


class MembershipView(TemplateView):
    template_name = 'community/membership.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'membership'
        ctx['features'] = [
            {'name': '나의 식비 리포트',   'free': False, 'paid': True,  'desc': '방문 식당·지출 패턴 분석'},
            {'name': '신규 정직 식당 알림', 'free': False, 'paid': True,  'desc': '내 지역 새 인증 식당 푸시'},
            {'name': '가격 인상 알림',     'free': False, 'paid': True,  'desc': '영수증 데이터 기반 가격 변화 감지'},
            {'name': '광고 제거',          'free': False, 'paid': True,  'desc': '광고 없는 깔끔한 화면'},
            {'name': '영수증 인증',        'free': True,  'paid': True,  'desc': ''},
            {'name': '리뷰 작성',          'free': True,  'paid': True,  'desc': ''},
            {'name': '북마크',             'free': True,  'paid': True,  'desc': ''},
            {'name': '뱃지·챌린지',        'free': True,  'paid': True,  'desc': ''},
        ]
        ctx['is_subscribed'] = False
        return ctx


class TourView(TemplateView):
    template_name = 'community/tour.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'tour'
        tours_raw = [
            {'title': '강남 골목 칼국수 투어', 'date': '2026.06.07 (토)',
             'spots': ['신목사골칼국수', '명동칼국수', '을지면옥'],
             'participants': 18, 'max': 30, 'pct': 60,
             'badge': '강남 탐험가 뱃지', 'dday': 9, 'region': '강남구', 'status': 'open'},
            {'title': '종로 노포 맛집 완전정복', 'date': '2026.06.14 (토)',
             'spots': ['청진옥', '이문설렁탕', '하동관'],
             'participants': 28, 'max': 30, 'pct': 93,
             'badge': '노포 수호자 뱃지', 'dday': 16, 'region': '종로구', 'status': 'almost'},
            {'title': '마포 트렌디 식당 탐방', 'date': '2026.06.21 (토)',
             'spots': ['망원동 맛집 A', '합정 맛집 B', '홍대 맛집 C'],
             'participants': 5, 'max': 25, 'pct': 20,
             'badge': '마포 탐험가 뱃지', 'dday': 23, 'region': '마포구', 'status': 'open'},
        ]
        for t in tours_raw:
            t['bar_class'] = 'prog-fill prog-warn' if t['pct'] >= 90 else 'prog-fill'
        ctx['upcoming_tours'] = tours_raw
        ctx['past_tours'] = [
            {'title': '서촌 한식 투어',    'date': '2026.05.03', 'participants': 24},
            {'title': '을지로 노포 탐방',  'date': '2026.04.19', 'participants': 30},
        ]
        return ctx


class MyReportView(LoginRequiredMixin, TemplateView):
    template_name = 'community/my_report.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'my-report'
        ctx['year']           = 2025
        ctx['total_visits']   = 47
        ctx['total_spent']    = 523000
        ctx['avg_per_visit']  = 11127
        ctx['review_count']   = 12
        ctx['bookmark_count'] = 28
        ctx['top_category']   = '칼국수·국수'
        ctx['top_region']     = '강남구'
        ctx['most_visited']   = '신목사골칼국수'
        ctx['most_visited_count'] = 6
        monthly_raw = [
            {'month': '1월',  'visits': 3,  'spent': 32000},
            {'month': '2월',  'visits': 4,  'spent': 41000},
            {'month': '3월',  'visits': 5,  'spent': 58000},
            {'month': '4월',  'visits': 3,  'spent': 27000},
            {'month': '5월',  'visits': 6,  'spent': 74000},
            {'month': '6월',  'visits': 4,  'spent': 43000},
            {'month': '7월',  'visits': 3,  'spent': 35000},
            {'month': '8월',  'visits': 5,  'spent': 62000},
            {'month': '9월',  'visits': 4,  'spent': 48000},
            {'month': '10월', 'visits': 4,  'spent': 45000},
            {'month': '11월', 'visits': 3,  'spent': 31000},
            {'month': '12월', 'visits': 3,  'spent': 27000},
        ]
        max_visits = max(m['visits'] for m in monthly_raw) or 1
        for m in monthly_raw:
            m['pct'] = round(m['visits'] / max_visits * 100)
        ctx['monthly_data'] = monthly_raw
        raw_cats = [
            {'name': '칼국수·국수', 'count': 14, 'pct': 30},
            {'name': '한식',        'count': 11, 'pct': 23},
            {'name': '분식',        'count': 8,  'pct': 17},
            {'name': '중식',        'count': 6,  'pct': 13},
            {'name': '기타',        'count': 8,  'pct': 17},
        ]
        for i, c in enumerate(raw_cats):
            c['bar_class'] = 'prog-gold' if i == 0 else ''
            c['label_class'] = 'cat-first' if i == 0 else 'cat-rest'
        ctx['category_data'] = raw_cats
        return ctx


class SocialView(LoginRequiredMixin, TemplateView):
    template_name = 'community/social.html'
    login_url     = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active'] = 'social'
        ctx['following_count'] = 5
        ctx['follower_count']  = 12
        ctx['following'] = [
            {'username': 'foodlover_kim', 'reviews': 87, 'certified': True,  'avatar': '🍜'},
            {'username': 'honest_eater',  'reviews': 72, 'certified': True,  'avatar': '🥢'},
            {'username': 'seoul_foodie',  'reviews': 65, 'certified': True,  'avatar': '🍱'},
            {'username': 'noodle_hunter', 'reviews': 51, 'certified': False, 'avatar': '🍝'},
            {'username': 'bapsim_jo',     'reviews': 34, 'certified': False, 'avatar': '🍚'},
        ]
        ctx['suggestions'] = [
            {'username': 'mapo_eater',   'reviews': 42, 'certified': True,  'avatar': '🌮', 'reason': '같은 지역 활동'},
            {'username': 'jongno_food',  'reviews': 38, 'certified': False, 'avatar': '🍛', 'reason': '비슷한 업종 취향'},
            {'username': 'gangnam_pick', 'reviews': 29, 'certified': False, 'avatar': '🥗', 'reason': '뱃지 공통 3개'},
        ]
        ctx['bookmarked_restaurants'] = [
            {'name': '신목사골칼국수', 'address': '서울 강남구', 'lat': 37.497, 'lng': 127.025},
            {'name': '형제육회',       'address': '서울 종로구', 'lat': 37.571, 'lng': 126.982},
            {'name': '을지면옥',       'address': '서울 중구',   'lat': 37.566, 'lng': 127.006},
        ]
        return ctx
