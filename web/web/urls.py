__all__ = ()

import django.conf.urls.static
from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import TemplateView

from social_core.exceptions import (
    AuthAlreadyAssociated,
    AuthCanceled,
    AuthException,
)

from social_django.views import complete


def custom_complete(request, backend, *args, **kwargs):
    try:
        return complete(request, backend, *args, **kwargs)
    except AuthAlreadyAssociated:
        messages.error(
            request,
            "Этот аккаунт уже привязан к другому пользователю.",
        )
        return redirect("accounts:profile")
    except AuthCanceled:
        messages.warning(
            request,
            "Авторизация была отменена или истек срок действия кода. Попробуйте снова.",
        )
        return redirect("accounts:auth")
    except AuthException as e:
        messages.error(request, f"Ошибка при входе: {str(e)}")
        return redirect("accounts:auth")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.homepage.urls")),
    path("about/", include("apps.about.urls")),
    path("auth/", include("apps.accounts.urls")),
    path("news/", include("apps.news.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("lessons/", include("apps.lessons.urls")),
    path("gamification/", include("apps.gamification.urls")),
    path(
        "oauth/complete/<str:backend>/",
        custom_complete,
        name="social_complete",
    ),
    path("oauth/", include("social_django.urls", namespace="social")),
]

urlpatterns += django.conf.urls.static.static(
    settings.STATIC_URL,
    document_root=settings.STATIC_ROOT,
)

urlpatterns += django.conf.urls.static.static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)

if settings.DEBUG:
    urlpatterns += [
        path("404/", TemplateView.as_view(template_name="404.html")),
        path("500/", TemplateView.as_view(template_name="500.html")),
    ]
