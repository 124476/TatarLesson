from apps.lessons import views

from django.urls import path

app_name = "lessons"

urlpatterns = [
    path("teacher/", views.TeacherDashboardView.as_view(), name="teacher_dashboard"),
    path("builder/", views.LessonBuilderView.as_view(), name="lesson_builder"),
    path("builder/<int:pk>/", views.LessonBuilderView.as_view(), name="lesson_edit"),
    path("save/", views.LessonSaveView.as_view(), name="lesson_save"),
    path("join/", views.LessonJoinView.as_view(), name="lesson_join"),
    path("play/<str:code>/", views.LessonPlayView.as_view(), name="lesson_play"),
    path("check/", views.BlockCheckView.as_view(), name="block_check"),
    path("finish/", views.LessonFinishView.as_view(), name="lesson_finish"),
    path("stats/<int:pk>/", views.LessonStatsView.as_view(), name="lesson_stats"),
    path("api/synthesize/", views.SynthesizeView.as_view(), name="api_synthesize"),
    path("api/recognize/", views.RecognizeView.as_view(), name="api_recognize"),
    path("api/translate/", views.TranslateView.as_view(), name="api_translate"),
]