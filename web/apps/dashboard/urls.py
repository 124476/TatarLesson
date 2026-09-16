from apps.dashboard import views

from django.urls import path

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("lessons/", views.LessonsListView.as_view(), name="lessons"),
    path("lessons/create/", views.LessonBuilderView.as_view(), name="lesson_builder"),
    path("lessons/<int:pk>/edit/", views.LessonBuilderView.as_view(), name="lesson_edit"),
    path("lessons/<int:pk>/stats/", views.LessonStatsView.as_view(), name="lesson_stats"),
    path("words/", views.WordsView.as_view(), name="words"),
    path("words/add/", views.AddWordView.as_view(), name="word_add"),
    path("words/<int:pk>/update/", views.UpdateWordView.as_view(), name="word_update"),
    path("words/<int:pk>/delete/", views.DeleteWordView.as_view(), name="word_delete"),
    path("competitions/", views.CompetitionsView.as_view(), name="competitions"),
]