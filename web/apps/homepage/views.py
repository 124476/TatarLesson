__all__ = ()

import random

from apps.words.models import Word

from django.views.generic import TemplateView


class Home(TemplateView):
    template_name = "homepage/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        count = Word.objects.count()
        ctx["random_word"] = (
            Word.objects.all()[random.randint(0, count - 1)] if count else None
        )
        return ctx
