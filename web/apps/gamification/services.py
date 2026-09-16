__all__ = ()

from datetime import timedelta

from apps.gamification.models import Achievement, UserAchievement

from django.contrib.auth.models import User
from django.utils import timezone


def add_points(user: User, points: int):
    """Начисляет очки пользователю."""
    profile = user.profile
    profile.points += points
    profile.save(update_fields=["points"])
    return profile.points


def update_streak(user: User):
    """Обновляет стрик ежедневных входов."""
    profile = user.profile
    today = timezone.localdate()

    if profile.last_login_date == today:
        return profile.streak

    if profile.last_login_date == today - timedelta(days=1):
        profile.streak += 1
    else:
        profile.streak = 1

    profile.last_login_date = today
    profile.save(update_fields=["streak", "last_login_date"])
    return profile.streak


def check_achievements(user: User):
    """Проверяет и выдаёт достижения."""
    profile = user.profile
    earned = []

    rules = [
        ("words_100", profile.points >= 1000, "🏅", "1000 очков"),
        ("streak_7", profile.streak >= 7, "🔥", "7 дней подряд"),
        ("streak_30", profile.streak >= 30, "💎", "30 дней подряд"),
    ]

    for code, condition, icon, title in rules:
        if condition:
            achievement, _ = Achievement.objects.get_or_create(
                code=code,
                defaults={"title": title, "icon": icon},
            )
            obj, created = UserAchievement.objects.get_or_create(
                user=user, achievement=achievement,
            )
            if created:
                earned.append(achievement)

    return earned


def levenshtein_ratio(a: str, b: str) -> float:
    """Сравнение строк (0..1). Без ML."""
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    len_a, len_b = len(a), len(b)
    matrix = [[0] * (len_b + 1) for _ in range(len_a + 1)]

    for i in range(len_a + 1):
        matrix[i][0] = i
    for j in range(len_b + 1):
        matrix[0][j] = j

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )

    distance = matrix[len_a][len_b]
    return 1 - distance / max(len_a, len_b)