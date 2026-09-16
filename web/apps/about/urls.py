from apps.about import views

from django.urls import path

app_name = "about"

urlpatterns = [
    path("", views.About.as_view(), name="about"),
]
