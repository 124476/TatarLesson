__all__ = ()

from apps.words.models import DailyWord, Word

from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(Word)
class WordAdmin(ModelAdmin):
    list_display = ("tatar", "russian", "transcription", "theme", "level")
    list_filter = ("theme", "level")
    search_fields = ("tatar", "russian", "transcription")
    ordering = ("theme", "tatar")
    compressed_fields = True

    fieldsets = (
        ("Основное", {
            "fields": ("tatar", "russian", "transcription"),
        }),
        ("Классификация", {
            "fields": ("theme", "level"),
        }),
        ("Примеры", {
            "fields": ("example_tt", "example_ru"),
        }),
        ("Медиа", {
            "fields": ("audio_url",),
        }),
    )


@admin.register(DailyWord)
class DailyWordAdmin(ModelAdmin):
    list_display = ("date", "word")
    list_filter = ("date",)
    search_fields = ("word__tatar", "word__russian")
    ordering = ("-date",)
    autocomplete_fields = ("word",)