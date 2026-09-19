__all__ = ()

from apps.core.models import BaseModel

from django.db import models


FALLBACK_THEME_NAMES = {
    "home":         "Дом",
    "house":        "Дом",
    "abstract":     "Абстрактные",
    "adjectives":   "Прилагательные",
    "adjective":    "Прилагательные",
    "adverbs":      "Наречия",
    "adverb":       "Наречия",
    "phrases":      "Фразы",
    "phrase":       "Фразы",
    "clothes":      "Одежда",
    "clothing":     "Одежда",
    "weather":      "Погода",
    "time":         "Время",
    "professions":  "Профессии",
    "profession":   "Профессии",
    "emotions":     "Эмоции",
    "emotion":      "Эмоции",
    "pronouns":     "Местоимения",
    "pronoun":      "Местоимения",
    "prepositions": "Предлоги",
    "preposition":  "Предлоги",
    "transport":    "Транспорт",
    "sports":       "Спорт",
    "music":        "Музыка",
    "art":          "Искусство",
    "science":      "Наука",
    "technology":   "Технологии",
    "business":     "Бизнес",
    "travel":       "Путешествия",
    "hobby":        "Хобби",
    "holidays":     "Праздники",
    "greetings":    "Приветствия",
    "kitchen":      "Кухня",
    "furniture":    "Мебель",
    "plants":       "Растения",
    "birds":        "Птицы",
    "insects":      "Насекомые",
    "sea":          "Море",
    "space":        "Космос",
    "quantity":     "Количество",
    "quality":      "Качества",
    "actions":      "Действия",
    "feelings":     "Чувства",
}


class Word(BaseModel):
    THEMES = (
        # базовые
        ("family",       "Семья"),
        ("food",         "Еда"),
        ("animals",      "Животные"),
        ("school",       "Школа"),
        ("nature",       "Природа"),
        ("city",         "Город"),
        ("body",         "Тело"),
        ("colors",       "Цвета"),
        ("numbers",      "Числа"),
        ("verbs",        "Глаголы"),

        # дом и быт
        ("home",         "Дом"),
        ("house",        "Дом"),
        ("furniture",    "Мебель"),
        ("kitchen",      "Кухня"),

        # люди и качества
        ("abstract",     "Абстрактные"),
        ("adjectives",   "Прилагательные"),
        ("adverbs",      "Наречия"),
        ("emotions",     "Эмоции"),
        ("feelings",     "Чувства"),
        ("pronouns",     "Местоимения"),
        ("prepositions", "Предлоги"),
        ("professions",  "Профессии"),

        # прочее
        ("clothes",      "Одежда"),
        ("weather",      "Погода"),
        ("time",         "Время"),
        ("phrases",      "Фразы"),
        ("greetings",    "Приветствия"),
        ("transport",    "Транспорт"),
        ("sports",       "Спорт"),
        ("music",        "Музыка"),
        ("art",          "Искусство"),
        ("science",      "Наука"),
        ("technology",   "Технологии"),
        ("travel",       "Путешествия"),
        ("holidays",     "Праздники"),
        ("plants",       "Растения"),
        ("birds",        "Птицы"),
        ("insects",      "Насекомые"),
        ("sea",          "Море"),
        ("space",        "Космос"),
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

    @property
    def theme_display(self):
        """
        Устойчивое отображение темы:
        1) Если ключ есть в THEMES — берём русское название.
        2) Иначе — ищем в FALLBACK_THEME_NAMES (легаси-ключи, AI-мусор).
        3) Совсем неизвестный — делаем Title-case из кода.
        """
        themes_dict = dict(self.THEMES)
        if self.theme in themes_dict:
            return themes_dict[self.theme]
        if self.theme in FALLBACK_THEME_NAMES:
            return FALLBACK_THEME_NAMES[self.theme]
        return str(self.theme or "").replace("_", " ").title()


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