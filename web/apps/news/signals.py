from apps.accounts.models import Notification
from apps.news.models import News

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.urls import reverse


@receiver(post_save, sender=News)
def notify_users_about_news(sender, instance, created, **kwargs):
    if created:
        users = User.objects.filter(is_active=True)

        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    profile=user.profile,
                    title=f"{instance.title}",
                    link=f"/news/{instance.id}/",
                    is_read=False
                )
            )

        if notifications:
            Notification.objects.bulk_create(notifications)