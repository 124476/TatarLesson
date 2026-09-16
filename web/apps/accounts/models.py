__all__ = ()

from apps.core.models import BaseModel

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class ClassGroup(BaseModel):
    name = models.CharField(max_length=64, verbose_name="Название")
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="classes",
        verbose_name="Учитель",
    )

    class Meta:
        verbose_name = "Класс"
        verbose_name_plural = "Классы"

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
    )
    avatar_url = models.URLField(
        blank=True,
        null=True,
    )

    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
    )
    email_verification_token_created = models.DateTimeField(
        blank=True,
        null=True,
    )

    new_email = models.EmailField(
        blank=True,
        null=True,
    )
    new_email_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
    )
    new_email_token_created = models.DateTimeField(
        blank=True,
        null=True,
    )

    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="students",
        verbose_name="Класс",
    )
    role = models.CharField(
        max_length=16,
        choices=(
            ("teacher", "Учитель"),
            ("student", "Ученик"),
            ("admin", "Администратор"),
        ),
        default="student",
        verbose_name="Роль",
    )
    points = models.PositiveIntegerField(default=0, verbose_name="Очки")
    streak = models.PositiveIntegerField(default=0, verbose_name="Стрик")
    last_login_date = models.DateField(null=True, blank=True)

    def get_avatar(self):
        if self.avatar:
            return self.avatar.url

        return self.avatar_url

    def unread_notifications_count(self):
        return self.notifications.filter(is_read=False).count()

    def __str__(self):
        return self.user.username


class Notification(BaseModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(
        max_length=255,
    )
    description = models.TextField(
        blank=True,
    )
    link = models.URLField(
        blank=True,
    )
    is_read = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return self.title


class ChatMessage(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    message = models.TextField()
    is_admin = models.BooleanField(
        default=False,
    )

    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = Profile.objects.create(user=instance)
        if instance.is_superuser or instance.is_staff:
            profile.email_verified = True
            profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
