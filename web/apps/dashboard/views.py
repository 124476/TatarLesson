__all__ = ()

import random

from apps.gamification.models import Duel
from apps.lessons.models import Answer, Lesson, LessonProgress
from apps.words.models import Word

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, TemplateView


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        count = Word.objects.count()
        if count:
            ctx["random_word"] = Word.objects.all()[random.randint(0, count - 1)]
        else:
            ctx["random_word"] = None
        return ctx


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
                finished_count=Count("progress", filter=Q(progress__is_finished=True), distinct=True),
            )
        )


class LessonBuilderView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/lesson_builder.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson_id = self.kwargs.get("pk")
        if lesson_id:
            lesson = get_object_or_404(Lesson, pk=lesson_id, author=self.request.user)
            ctx["lesson"] = lesson
            ctx["blocks"] = lesson.blocks.prefetch_related("words").all()
        return ctx


class LessonStatsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/lesson_stats.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = get_object_or_404(Lesson, pk=self.kwargs["pk"], author=self.request.user)
        progress = LessonProgress.objects.filter(lesson=lesson).select_related("user")

        ctx["lesson"] = lesson
        ctx["total_students"] = progress.count()
        ctx["finished"] = progress.filter(is_finished=True).count()
        ctx["in_progress"] = progress.filter(is_finished=False).count()
        ctx["top"] = progress.order_by("-score")[:10]

        block_stats = (
            Answer.objects
            .filter(block__lesson=lesson)
            .values("block__type", "block__id")
            .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
        )
        for b in block_stats:
            b["accuracy"] = round(b["correct"] / b["total"] * 100) if b["total"] else 0
        ctx["block_stats"] = block_stats
        return ctx


class LeaderboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/leaderboard.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        class_id = self.request.GET.get("class_id")
        qs = User.objects.filter(is_staff=False, is_active=True)
        if class_id:
            qs = qs.filter(profile__class_group_id=class_id)
        ctx["leaders"] = qs.order_by("-profile__points")[:50]
        ctx["my_points"] = self.request.user.profile.points
        ctx["my_streak"] = self.request.user.profile.streak
        return ctx


class DictionaryView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dictionary.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        word_ids = (
            Answer.objects
            .filter(user=self.request.user)
            .values_list("block__words__id", flat=True)
            .distinct()
        )
        ctx["words"] = Word.objects.filter(id__in=word_ids).order_by("theme", "tatar")
        themes = {}
        for w in ctx["words"]:
            themes.setdefault(w.get_theme_display(), []).append(w)
        ctx["themes"] = themes
        return ctx


class DuelView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/duel.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        duel = get_object_or_404(Duel, pk=self.kwargs["pk"])
        if self.request.user not in (duel.player1, duel.player2):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        ctx["duel"] = duel
        return ctx


# ===== Тест API =====
class TestAPIView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/test_api.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.lessons.api import TatSoftAPI

        # TTS
        try:
            audio = TatSoftAPI.synthesize("Ат")
            ctx["tts_status"] = f"OK ({len(audio)} байт)" if audio else "FAIL"
            ctx["tts_ok"] = bool(audio)
        except Exception as e:
            ctx["tts_status"] = f"ERROR: {e}"
            ctx["tts_ok"] = False

        # MT
        try:
            result = TatSoftAPI.translate("Привет", "ru", "tt")
            ctx["mt_status"] = f"OK: {result}" if result else "FAIL"
            ctx["mt_ok"] = bool(result)
        except Exception as e:
            ctx["mt_status"] = f"ERROR: {e}"
            ctx["mt_ok"] = False

        # Morph
        try:
            morph = TatSoftAPI.morphology("Мин китап укыйм")
            ctx["morph_status"] = f"OK ({len(morph) if morph else 0} элементов)" if morph else "FAIL"
            ctx["morph_ok"] = bool(morph)
        except Exception as e:
            ctx["morph_status"] = f"ERROR: {e}"
            ctx["morph_ok"] = False

        return ctx