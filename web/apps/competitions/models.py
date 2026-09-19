__all__ = ()

from apps.core.models import BaseModel

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Competition(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    start_time = models.DateTimeField(verbose_name="Начало")
    end_time = models.DateTimeField(verbose_name="Окончание")
    is_published = models.BooleanField(default=False, verbose_name="Опубликовано")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name="created_competitions",
    )

    class Meta:
        verbose_name = "Соревнование"
        verbose_name_plural = "Соревнования"
        ordering = ("-start_time",)

    def __str__(self):
        return self.title

    def get_status(self):
        now = timezone.now()
        if now < self.start_time:
            return "upcoming"
        if now > self.end_time:
            return "finished"
        return "running"

    def is_running(self):
        return self.get_status() == "running"

    def is_finished(self):
        return self.get_status() == "finished"

    def is_upcoming(self):
        return self.get_status() == "upcoming"

    def total_points(self):
        return sum(t.points for t in self.tasks.all())


class CompetitionTask(BaseModel):
    """
    Задача. Типы:
    - text: ввод текста (перевод, ответ)
    - choice: один вариант из списка
    - multiple_choice: несколько вариантов (нужно выбрать все правильные)
    - build: собрать слово из букв
    - pairs: соединить пары стрелками
    - voice: голосовой ответ (распознавание речи)
    """
    TYPES = (
        ("text", "Текстовый ответ"),
        ("choice", "Один вариант"),
        ("multiple_choice", "Несколько вариантов"),
        ("build", "Собери слово"),
        ("pairs", "Найди пару"),
        ("voice", "Голосовой перевод"),
    )

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="tasks",
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    statement = models.TextField(verbose_name="Условие")

    task_type = models.CharField(
        max_length=32, choices=TYPES, default="text", verbose_name="Тип",
    )

    # Для text / choice / multiple_choice / voice
    correct_answer = models.CharField(
        max_length=255, blank=True, verbose_name="Правильный ответ",
    )

    # Для choice / multiple_choice: [{"text": "...", "is_correct": true}, ...]
    options = models.JSONField(default=list, blank=True, verbose_name="Варианты")

    # Для build: слово для сборки
    build_word = models.CharField(max_length=128, blank=True, verbose_name="Слово для сборки")
    # Для build: подсказка (перевод на русский)
    build_hint = models.CharField(max_length=255, blank=True, verbose_name="Подсказка")

    # Для pairs: [["татарский", "русский"], ...]
    pairs = models.JSONField(default=list, blank=True, verbose_name="Пары")

    # Для voice: текст для произнесения
    voice_text = models.CharField(max_length=255, blank=True, verbose_name="Текст для произнесения")

    points = models.PositiveIntegerField(default=100, verbose_name="Баллы")
    max_attempts = models.PositiveIntegerField(default=5, verbose_name="Максимум попыток")
    order_index = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        verbose_name = "Задача соревнования"
        verbose_name_plural = "Задачи соревнования"
        ordering = ("order_index", "id")

    def __str__(self):
        return f"{self.competition.title} → {self.title}"


class Submission(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="submissions",
    )
    task = models.ForeignKey(
        CompetitionTask, on_delete=models.CASCADE, related_name="submissions",
    )
    answer = models.TextField(verbose_name="Ответ")
    is_correct = models.BooleanField(default=False, verbose_name="Верно")
    points_earned = models.PositiveIntegerField(default=0, verbose_name="Баллы")
    attempt_number = models.PositiveIntegerField(default=1, verbose_name="Номер попытки")

    class Meta:
        verbose_name = "Посылка"
        verbose_name_plural = "Посылки"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} → {self.task.title}"


class CompetitionParticipant(BaseModel):
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="participants",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="competition_participations",
    )
    score = models.PositiveIntegerField(default=0, verbose_name="Баллы")

    class Meta:
        verbose_name = "Участник соревнования"
        verbose_name_plural = "Участники соревнований"
        unique_together = ("competition", "user")
        ordering = ("-score", "created_at")

    def __str__(self):
        return f"{self.user.username} ({self.competition.title}) — {self.score}"