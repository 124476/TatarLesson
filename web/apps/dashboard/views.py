__all__ = ()

import random

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from apps.lessons.models import Answer, Lesson, LessonProgress
from apps.words.models import Word

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse
from django.views import View


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"
    login_url = "accounts:auth"


class LessonsListView(LoginRequiredMixin, ListView):
    template_name = "dashboard/lessons.html"
    context_object_name = "lessons"
    login_url = "accounts:auth"

    def get_queryset(self):
        return (
            Lesson.objects
            .filter(author=self.request.user)
            .prefetch_related("blocks")
            .annotate(
                total_students=Count("progress", distinct=True),
                finished_count=Count(
                    "progress",
                    filter=Q(progress__is_finished=True),
                    distinct=True,
                ),
            )
        )


class LessonBuilderView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/lesson_builder.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson_id = self.kwargs.get("pk")

        ctx["all_words"] = Word.objects.all().order_by("theme", "tatar")

        if lesson_id:
            import json
            lesson = get_object_or_404(
                Lesson, pk=lesson_id, author=self.request.user,
            )
            ctx["lesson"] = lesson

            blocks = list(lesson.blocks.prefetch_related("words").all())
            for block in blocks:
                block.config_json = json.dumps(block.config or {},
                                               ensure_ascii=False)
            ctx["blocks"] = blocks

        return ctx


class LessonStatsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/lesson_stats.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = get_object_or_404(
            Lesson, pk=self.kwargs["pk"], author=self.request.user,
        )
        progress = LessonProgress.objects.filter(lesson=lesson).select_related(
            "user")
        ctx["lesson"] = lesson
        ctx["total_students"] = progress.count()
        ctx["finished"] = progress.filter(is_finished=True).count()
        ctx["in_progress"] = progress.filter(is_finished=False).count()
        ctx["top"] = progress.order_by("-score")[:10]
        return ctx


class WordsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/words.html"
    login_url = "accounts:auth"
    PER_PAGE = 24

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        search = self.request.GET.get("q", "").strip()
        theme = self.request.GET.get("theme", "").strip()
        page = self.request.GET.get("page", 1)

        qs = Word.objects.all()
        if search:
            qs = qs.filter(
                Q(tatar__icontains=search) | Q(russian__icontains=search))
        if theme:
            qs = qs.filter(theme=theme)
        qs = qs.order_by("tatar")

        paginator = Paginator(qs, self.PER_PAGE)
        try:
            page_obj = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        ctx["words"] = page_obj.object_list
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["total_count"] = paginator.count
        ctx["themes"] = Word.THEMES
        ctx["search"] = search
        ctx["selected_theme"] = theme
        ctx["is_admin"] = self.request.user.is_staff
        return ctx


class AddWordView(LoginRequiredMixin, View):
    """API: добавление слова. Только для админа."""
    login_url = "accounts:auth"

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)

        import json
        data = json.loads(request.body)

        tatar = data.get("tatar", "").strip()
        russian = data.get("russian", "").strip()
        transcription = data.get("transcription", "").strip()
        example_tt = data.get("example_tt", "").strip()
        example_ru = data.get("example_ru", "").strip()
        theme = data.get("theme", "family").strip()

        if not tatar or not russian:
            return JsonResponse({"error": "Заполните слово и перевод"},
                                status=400)

        if Word.objects.filter(tatar__iexact=tatar).exists():
            return JsonResponse({"error": "Такое слово уже есть"}, status=400)

        word = Word.objects.create(
            tatar=tatar,
            russian=russian,
            transcription=transcription,
            example_tt=example_tt,
            example_ru=example_ru,
            theme=theme,
        )

        return JsonResponse({
            "status": "ok",
            "id": word.id,
            "word": {
                "tatar": word.tatar,
                "russian": word.russian,
                "transcription": word.transcription,
                "theme": word.theme,
                "theme_display": word.get_theme_display(),
            },
        })


class UpdateWordView(LoginRequiredMixin, View):
    """API: редактирование слова. Только для админа."""
    login_url = "accounts:auth"

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)

        import json
        data = json.loads(request.body)
        word = get_object_or_404(Word, pk=pk)

        word.tatar = data.get("tatar", word.tatar).strip()
        word.russian = data.get("russian", word.russian).strip()
        word.transcription = data.get("transcription",
                                      word.transcription).strip()
        word.example_tt = data.get("example_tt", word.example_tt).strip()
        word.example_ru = data.get("example_ru", word.example_ru).strip()
        word.theme = data.get("theme", word.theme)
        word.save()

        return JsonResponse({"status": "ok"})


class DeleteWordView(LoginRequiredMixin, View):
    """API: удаление слова. Только для админа."""
    login_url = "accounts:auth"

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)

        word = get_object_or_404(Word, pk=pk)
        word.delete()
        return JsonResponse({"status": "ok"})
