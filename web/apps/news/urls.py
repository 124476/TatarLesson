from apps.news import views

from django.urls import path

app_name = "news"

urlpatterns = [
    path("", views.NewsListView.as_view(), name="list"),
    path("<int:pk>/", views.NewsDetailView.as_view(), name="detail"),
]
