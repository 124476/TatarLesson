from apps.dashboard import views

from django.urls import path

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("lessons/", views.LessonsListView.as_view(), name="lessons"),
    path("lessons/create/", views.LessonBuilderView.as_view(), name="lesson_builder"),
    path("lessons/<int:pk>/edit/", views.LessonBuilderView.as_view(), name="lesson_edit"),
    path("lessons/<int:pk>/stats/", views.LessonStatsView.as_view(), name="lesson_stats"),
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
    path("dictionary/", views.DictionaryView.as_view(), name="dictionary"),
    path("duel/<int:pk>/", views.DuelView.as_view(), name="duel"),
    path("test-api/", views.TestAPIView.as_view(), name="test_api"),
]