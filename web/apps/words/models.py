__all__ = ()

from apps.core.models import BaseModel

from django.db import models


class Word(BaseModel):
    THEMES = (
        ("family", "Семья"),
        ("food", "Еда"),
        ("animals", "Животные"),
        ("school", "Школа"),
        ("nature", "Природа"),
        ("city", "Город"),
        ("body", "Тело"),
        ("colors", "Цвета"),
        ("numbers", "Числа"),
        ("verbs", "Глаголы"),
    )
    LEVELS = (
        ("beginner", "Начальный"),
        ("intermediate", "Средний"),
        ("advanced", "Продвинутый"),
    )

    tatar = models.CharField(max_length=128, verbose_name="Татарское слово")
    russian = models.CharField(max_length=128, verbose_name="Русский перевод")
    transcription = models.CharField(
        max_length=128, blank=True, verbose_name="Транскрипция",
    )
    example_tt = models.CharField(
        max_length=255, blank=True, verbose_name="Пример (татарский)",
    )
    example_ru = models.CharField(
        max_length=255, blank=True, verbose_name="Пример (русский)",
    )
    theme = models.CharField(
        max_length=32, choices=THEMES, default="family", verbose_name="Тема",
    )
    level = models.CharField(
        max_length=32, choices=LEVELS, default="beginner", verbose_name="Уровень",
    )
    audio_url = models.URLField(blank=True, verbose_name="Ссылка на аудио")

    class Meta:
        verbose_name = "Слово"
        verbose_name_plural = "Слова"
        ordering = ("tatar",)

    def __str__(self):
        return f"{self.tatar} — {self.russian}"


class DailyWord(BaseModel):
    word = models.ForeignKey(
        Word, on_delete=models.CASCADE, related_name="daily_entries",
    )
    date = models.DateField(unique=True, verbose_name="Дата")

    class Meta:
        verbose_name = "Слово дня"
        verbose_name_plural = "Слова дня"
        ordering = ("-date",)

    def __str__(self):
        return f"{self.date}: {self.word.tatar}"