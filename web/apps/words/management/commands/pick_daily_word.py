__all__ = ()

import random

from apps.words.models import DailyWord, Word

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Выбирает слово дня на сегодня"

    def handle(self, *args, **options):
        today = timezone.localdate()

        if DailyWord.objects.filter(date=today).exists():
            self.stdout.write(self.style.WARNING("Слово дня уже выбрано"))
            return

        used_ids = DailyWord.objects.values_list("word_id", flat=True)
        candidates = Word.objects.exclude(id__in=used_ids)

        if not candidates.exists():
            candidates = Word.objects.all()

        word = random.choice(list(candidates))
        DailyWord.objects.create(word=word, date=today)
        self.stdout.write(
            self.style.SUCCESS(f"Слово дня: {word.tatar} — {word.russian}"),
        )