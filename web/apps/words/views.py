__all__ = ()

from django.views.generic import TemplateView


class Words(TemplateView):
    template_name = "words/words.html"
