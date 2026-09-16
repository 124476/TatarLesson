__all__ = ()

from apps.core.models import BaseModel

from django.contrib.auth.models import User
from django.db import models


class Duel(BaseModel):
    player1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="duels_as_p1",
    )
    player2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="duels_as_p2",
    )
    winner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="duels_won",
    )
    score1 = models.PositiveIntegerField(default=0)
    score2 = models.PositiveIntegerField(default=0)
    is_finished = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Дуэль"
        verbose_name_plural = "Дуэли"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username}"


class Achievement(BaseModel):
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=16, default="🏅")

    class Meta:
        verbose_name = "Достижение"
        verbose_name_plural = "Достижения"

    def __str__(self):
        return self.title


class UserAchievement(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="achievements",
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Достижение пользователя"
        verbose_name_plural = "Достижения пользователей"
        unique_together = ("user", "achievement")

    def __str__(self):
        return f"{self.user.username} — {self.achievement.title}"