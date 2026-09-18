from apps.competitions import views

from django.urls import path

app_name = "competitions"

urlpatterns = [
    path("", views.CompetitionListView.as_view(), name="list"),
    path("<int:pk>/", views.CompetitionDetailView.as_view(), name="detail"),
    path("<int:pk>/task/<int:task_id>/", views.CompetitionTaskView.as_view(), name="task"),
    path("<int:pk>/submit/<int:task_id>/", views.SubmitSolutionView.as_view(), name="submit"),
    path("api/synthesize/", views.CompetitionSynthesizeView.as_view(), name="api_synthesize"),
    path("api/recognize/", views.CompetitionRecognizeView.as_view(), name="api_recognize"),
    path("api/words/", views.CompetitionWordsAPIView.as_view(), name="api_words"),
    path("manage/", views.CompetitionAdminListView.as_view(), name="admin_list"),
    path("manage/create/", views.CompetitionAdminCreateView.as_view(), name="admin_create"),
    path("manage/<int:pk>/edit/", views.CompetitionAdminCreateView.as_view(), name="admin_edit"),
    path("manage/save/", views.CompetitionAdminSaveView.as_view(), name="admin_save"),
    path("manage/<int:pk>/delete/", views.CompetitionAdminDeleteView.as_view(), name="admin_delete"),
]