from apps.homepage import views

from django.urls import path

app_name = "homepage"

urlpatterns = [
    path("", views.Home.as_view(), name="home"),
]
