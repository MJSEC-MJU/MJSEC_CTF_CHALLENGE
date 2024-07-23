from django.urls import path
from . import views
app_name = 'challenges'
urlpatterns = [
    path('', views.index, name='index'),
    path('feeds/', views.feeds, name='feeds'),
    path('challenge/<int:challenge_id>/', views.challenge_detail, name='challenge_detail'),
    path('submit/', views.submit_flag, name='submit_flag'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('problem_stats/', views.problem_stats, name='problem_stats'),
    path('submission_stats/', views.submission_stats, name='submission_stats'),
]
