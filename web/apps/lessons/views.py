__all__ = ()

import json

from apps.gamification.services import (
    add_points,
    check_achievements,
    levenshtein_ratio,
    update_streak,
)
from apps.lessons.api import TatSoftAPI
from apps.lessons.models import Answer, Block, Lesson, LessonProgress
from apps.words.models import DailyWord, Word

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView


class TeacherDashboardView(LoginRequiredMixin, ListView):
    template_name = "lessons/teacher_dashboard.html"
    context_object_name = "lessons"
    login_url = "accounts:auth"

    def get_queryset(self):
        return Lesson.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["classes"] = self.request.user.classes.all()
        return ctx


class LessonBuilderView(LoginRequiredMixin, TemplateView):
    template_name = "lessons/lesson_builder.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["block_types"] = Block.TYPES
        ctx["themes"] = Word.THEMES
        lesson_id = self.kwargs.get("pk")
        if lesson_id:
            ctx["lesson"] = get_object_or_404(
                Lesson, pk=lesson_id, author=self.request.user,
            )
            ctx["blocks"] = ctx["lesson"].blocks.all()
        return ctx


class LessonSaveView(LoginRequiredMixin, View):
    """API: сохранение урока из конструктора."""

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        lesson_id = data.get("lesson_id")
        title = data.get("title", "Без названия")
        blocks_data = data.get("blocks", [])

        if lesson_id:
            lesson = get_object_or_404(
                Lesson, pk=lesson_id, author=request.user,
            )
            lesson.title = title
            lesson.save()
            lesson.blocks.all().delete()
        else:
            lesson = Lesson.objects.create(
                title=title,
                author=request.user,
                is_public=data.get("is_public", False),
            )

        for i, b in enumerate(blocks_data):
            block = Block.objects.create(
                lesson=lesson,
                type=b["type"],
                order_index=i,
                points=b.get("points", 10),
                config=b.get("config", {}),
            )
            word_ids = b.get("word_ids", [])
            if word_ids:
                block.words.set(Word.objects.filter(id__in=word_ids))

        return JsonResponse({"status": "ok", "lesson_id": lesson.id, "code": lesson.code})


class LessonPlayView(LoginRequiredMixin, TemplateView):
    template_name = "lessons/lesson_play.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        import json
        ctx = super().get_context_data(**kwargs)
        lesson = get_object_or_404(Lesson, code=self.kwargs["code"])
        ctx["lesson"] = lesson

        blocks = list(lesson.blocks.prefetch_related("words").all())
        for block in blocks:
            if block.config and "pairs" in block.config:
                block.config["pairs_json"] = json.dumps(
                    block.config["pairs"], ensure_ascii=False,
                )
            else:
                block.config["pairs_json"] = "[]"

        ctx["blocks"] = blocks

        progress, _ = LessonProgress.objects.get_or_create(
            user=self.request.user, lesson=lesson,
        )
        ctx["progress"] = progress
        return ctx


class BlockCheckView(LoginRequiredMixin, View):
    """API: проверка ответа ученика."""

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        block = get_object_or_404(Block, pk=data["block_id"])
        user_answer = data.get("answer", "").strip()
        time_spent = data.get("time_spent", 0)

        is_correct = False
        earned = 0
        feedback = ""

        if block.type == "translate":
            correct = block.config.get("correct", "").strip()
            ratio = levenshtein_ratio(user_answer, correct)
            is_correct = ratio >= 0.8
            feedback = f"Точность: {int(ratio * 100)}%"

        elif block.type == "audio":
            correct = block.config.get("correct", "").strip()
            ratio = levenshtein_ratio(user_answer, correct)
            is_correct = ratio >= 0.8

        elif block.type == "quick":
            correct = block.config.get("correct", "").strip()
            is_correct = user_answer.lower() == correct.lower()

        elif block.type == "gap":
            correct = str(block.config.get("correct", "")).strip()
            is_correct = user_answer.lower() == correct.lower()

        elif block.type == "build":
            correct = block.config.get("word", "").strip()
            is_correct = user_answer.lower() == correct.lower()

        elif block.type == "pairs":
            is_correct = user_answer == "pairs_complete"

        if is_correct:
            earned = block.points
            add_points(request.user, earned)

        Answer.objects.create(
            user=request.user,
            block=block,
            answer=user_answer,
            is_correct=is_correct,
            points_earned=earned,
            time_spent=time_spent,
        )

        update_streak(request.user)
        check_achievements(request.user)

        return JsonResponse({
            "is_correct": is_correct,
            "points": earned,
            "feedback": feedback,
        })


class LessonJoinView(LoginRequiredMixin, View):
    """Ученик вводит код урока."""

    def post(self, request, *args, **kwargs):
        code = request.POST.get("code", "").strip()
        lesson = Lesson.objects.filter(code=code).first()
        if not lesson:
            return JsonResponse({"error": "Урок не найден"}, status=404)
        return JsonResponse({"status": "ok", "url": f"/lessons/play/{code}/"})


class LessonFinishView(LoginRequiredMixin, View):
    """Завершение урока."""

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        lesson = get_object_or_404(Lesson, pk=data["lesson_id"])
        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson,
        )
        progress.is_finished = True
        progress.finished_at = timezone.now()
        progress.score = sum(
            a.points_earned for a in Answer.objects.filter(
                user=request.user, block__lesson=lesson,
            )
        )
        progress.save()
        return JsonResponse({"status": "ok", "score": progress.score})


class LessonStatsView(LoginRequiredMixin, TemplateView):
    template_name = "lessons/lesson_stats.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = get_object_or_404(
            Lesson, pk=self.kwargs["pk"], author=self.request.user,
        )
        progress = LessonProgress.objects.filter(lesson=lesson)
        ctx["lesson"] = lesson
        ctx["total_students"] = progress.count()
        ctx["finished"] = progress.filter(is_finished=True).count()
        ctx["in_progress"] = progress.filter(is_finished=False).count()
        ctx["top"] = progress.order_by("-score")[:5]
        return ctx


class SynthesizeView(View):
    """API: озвучка текста через TatSoft."""

    def get(self, request, *args, **kwargs):
        text = request.GET.get("text", "").strip()
        speaker = request.GET.get("speaker", "alsu")

        if not text:
            return JsonResponse({"error": "no text"}, status=400)

        audio = TatSoftAPI.synthesize(text, speaker=speaker)
        if not audio:
            return JsonResponse({"error": "tts failed"}, status=502)

        from django.http import HttpResponse
        return HttpResponse(audio, content_type="audio/wav")


class RecognizeView(View):
    """API: распознавание речи через TatSoft."""

    def post(self, request, *args, **kwargs):
        audio = request.FILES.get("audio")
        if not audio:
            return JsonResponse({"error": "no audio"}, status=400)
        text = TatSoftAPI.recognize(audio.read())
        return JsonResponse({"text": text or ""})


class TranslateView(View):
    """API: перевод через TatSoft."""

    def get(self, request, *args, **kwargs):
        text = request.GET.get("text", "")
        src = request.GET.get("src", "ru")
        dst = request.GET.get("dst", "tt")
        translation = TatSoftAPI.translate(text, src, dst)
        return JsonResponse({"translation": translation or ""})