from apps.lessons import views

from django.urls import path

app_name = "lessons"

urlpatterns = [
    path("save/", views.LessonSaveView.as_view(), name="lesson_save"),
    path("join/", views.LessonJoinView.as_view(), name="lesson_join"),
    path("play/<str:code>/", views.LessonPlayView.as_view(), name="lesson_play"),
    path("submit/", views.LessonSubmitView.as_view(), name="lesson_submit"),  # ← вместо check
    path("stats/<int:pk>/", views.LessonStatsView.as_view(), name="lesson_stats"),
    path("api/synthesize/", views.SynthesizeView.as_view(), name="api_synthesize"),
    path("api/recognize/", views.RecognizeView.as_view(), name="api_recognize"),
    path("api/translate/", views.TranslateView.as_view(), name="api_translate"),
]