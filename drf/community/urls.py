from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('badges/',       views.BadgeView.as_view(),      name='badges'),
    path('challenge/',    views.ChallengeView.as_view(),  name='challenge'),
    path('price-report/', views.PriceReportView.as_view(),name='price-report'),
    path('reviewer/',     views.ReviewerView.as_view(),   name='reviewer'),
    path('membership/',   views.MembershipView.as_view(), name='membership'),
    path('tour/',         views.TourView.as_view(),       name='tour'),
    path('my-report/',    views.MyReportView.as_view(),   name='my-report'),
    path('social/',       views.SocialView.as_view(),     name='social'),
]
