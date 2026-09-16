__all__ = ()

from apps.core.models import BaseModel
from apps.words.models import Word

from django.contrib.auth.models import User
from django.db import models


class Lesson(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Название")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lessons",
    )
    class_group = models.ForeignKey(
        "accounts.ClassGroup",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="lessons",
        verbose_name="Класс",
    )
    is_public = models.BooleanField(
        default=False, verbose_name="Публичный (для самостоятельного обучения)",
    )
    code = models.CharField(
        max_length=6, unique=True, blank=True, verbose_name="Код урока",
    )
    time_limit = models.PositiveIntegerField(
        default=15, verbose_name="Лимит времени (мин)",
    )
    leaderboard_on = models.BooleanField(
        default=True, verbose_name="Показывать лидерборд",
    )

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.code:
            import random
            self.code = "".join(
                str(random.randint(0, 9)) for _ in range(6)
            )
        super().save(*args, **kwargs)

    def total_points(self):
        return sum(b.points for b in self.blocks.all())

    def __str__(self):
        return self.title


class Block(BaseModel):
    TYPES = (
        ("audio", "🎧 Аудирование"),
        ("translate", "📖 Перевод"),
        ("speak", "🎙️ Произношение"),
        ("build", "🧩 Собери слово"),
        ("pairs", "🔗 Найди пару"),
        ("gap", "📝 Вставь пропуск"),
        ("dialog", "💬 Диалог"),
        ("crossword", "🧩 Кроссворд"),
        ("quick", "⏱️ Быстрый раунд"),
        ("creative", "🎨 Творческое"),
    )

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="blocks",
    )
    type = models.CharField(max_length=32, choices=TYPES, verbose_name="Тип")
    order_index = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    points = models.PositiveIntegerField(default=10, verbose_name="Баллы")
    config = models.JSONField(default=dict, verbose_name="Настройки")
    words = models.ManyToManyField(
        Word, blank=True, related_name="blocks", verbose_name="Слова",
    )

    class Meta:
        verbose_name = "Блок"
        verbose_name_plural = "Блоки"
        ordering = ("order_index",)

    def __str__(self):
        return f"{self.get_type_display()} ({self.lesson.title})"


class Answer(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="answers",
    )
    block = models.ForeignKey(
        Block, on_delete=models.CASCADE, related_name="answers",
    )
    answer = models.TextField(blank=True, verbose_name="Ответ")
    is_correct = models.BooleanField(default=False, verbose_name="Верно")
    points_earned = models.PositiveIntegerField(default=0, verbose_name="Баллы")
    time_spent = models.PositiveIntegerField(default=0, verbose_name="Время (сек)")

    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} → {self.block}"


class LessonProgress(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="progress",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0, verbose_name="Итоговый балл")
    is_finished = models.BooleanField(default=False, verbose_name="Завершён")

    class Meta:
        verbose_name = "Прогресс по уроку"
        verbose_name_plural = "Прогресс по урокам"
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.username} — {self.lesson.title}"