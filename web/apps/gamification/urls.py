from apps.gamification import views

from django.urls import path

app_name = "gamification"

urlpatterns = [
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
    path("duel/create/", views.DuelCreateView.as_view(), name="duel_create"),
    path("duel/<int:pk>/", views.DuelView.as_view(), name="duel"),
    path("duel/finish/", views.DuelFinishView.as_view(), name="duel_finish"),
    path("api/top/", views.TopUsersAPI.as_view(), name="api_top"),
]