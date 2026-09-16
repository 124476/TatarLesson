from apps.words import views

from django.urls import path

app_name = "words"

urlpatterns = [
    path("", views.Words.as_view(), name="words"),
]
