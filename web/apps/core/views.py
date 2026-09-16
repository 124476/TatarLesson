__all__ = ()

from apps.accounts.models import Notification, User


def dashboard_callback(request, context):
    context.update(
        {
            "cards": [
                {
                    "title": "Пользователи",
                    "value": User.objects.count(),
                    "icon": "person",
                },
                {
                    "title": "Уведомления",
                    "value": Notification.objects.count(),
                    "icon": "notifications",
                },
            ],
        },
    )
    return context
