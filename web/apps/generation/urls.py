from apps.generation import views

from django.urls import path

app_name = "generation"

urlpatterns = [
    # Чат
    path("chat/", views.AIChatView.as_view(), name="chat"),
    path("chat/send/", views.AIChatSendView.as_view(), name="chat_send"),
    path("chat/clear/", views.AIChatClearView.as_view(), name="chat_clear"),

    # Генерация
    path("words/", views.GenerateWordsView.as_view(), name="words"),
    path("distractors/", views.GenerateDistractorsView.as_view(), name="distractors"),
    path("explain/", views.ExplainView.as_view(), name="explain"),
    path("competition-tasks/", views.GenerateCompetitionTasksView.as_view(), name="competition_tasks"),
]
