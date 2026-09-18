__all__ = ()

from apps.core.models import BaseModel

from django.contrib.auth.models import User
from django.db import models


class AIChatMessage(BaseModel):
    ROLE_CHOICES = (
        ("user", "Пользователь"),
        ("assistant", "Ассистент"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ai_chat_messages",
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()

    class Meta:
        verbose_name = "AI-сообщение"
        verbose_name_plural = "AI-сообщения"
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} [{self.role}]: {self.content[:50]}"
