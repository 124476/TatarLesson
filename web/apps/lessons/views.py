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


class LessonSaveView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        lesson_id = data.get("lesson_id")
        title = data.get("title", "Без названия")
        blocks_data = data.get("blocks", [])
        allow_retry = data.get("allow_retry", True)
        is_public = data.get("is_public", False)
        is_competition = data.get("is_competition", False)
        show_answers_after = data.get("show_answers_after", False)

        valid_types = {t[0] for t in Block.TYPES}
        blocks_data = [b for b in blocks_data if b.get("type") in valid_types]

        if lesson_id:
            lesson = get_object_or_404(Lesson, pk=lesson_id, author=request.user)
            lesson.title = title
            lesson.is_public = is_public
            lesson.is_competition = is_competition
            lesson.allow_retry = allow_retry
            lesson.show_answers_after = show_answers_after
            lesson.save()
            lesson.blocks.all().delete()
        else:
            lesson = Lesson.objects.create(
                title=title,
                author=request.user,
                is_public=is_public,
                is_competition=is_competition,
                allow_retry=allow_retry,
                show_answers_after=show_answers_after,
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

        return JsonResponse({
            "status": "ok",
            "lesson_id": lesson.id,
            "code": lesson.code,
        })


class LessonPlayView(LoginRequiredMixin, TemplateView):
    template_name = "lessons/lesson_play.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = get_object_or_404(Lesson, code=self.kwargs["code"])
        ctx["lesson"] = lesson

        progress = LessonProgress.objects.filter(
            user=self.request.user, lesson=lesson,
        ).first()

        # Урок уже пройден и повтор запрещён — показываем результат
        if progress and progress.is_finished and not lesson.allow_retry:
            ctx["already_finished"] = True
            ctx["progress"] = progress

            if lesson.show_answers_after:
                answers = {
                    a.block_id: a
                    for a in Answer.objects.filter(
                        user=self.request.user, block__lesson=lesson,
                    )
                }
                summary = []
                for block in lesson.blocks.all().order_by("order_index"):
                    a = answers.get(block.id)
                    summary.append({
                        "type_display": block.get_type_display(),
                        "type": block.type,
                        "user_answer": a.answer if a else "—",
                        "is_correct": a.is_correct if a else False,
                        "points": a.points_earned if a else 0,
                        "max_points": block.points,
                        "correct": block.config.get("correct", ""),
                        "pairs": block.config.get("pairs", []),
                    })
                ctx["answers_summary"] = summary
            else:
                ctx["answers_summary"] = None
            return ctx

        ctx["already_finished"] = False
        ctx["answers_summary"] = None

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


class LessonJoinView(LoginRequiredMixin, View):
    """Ученик вводит код урока."""

    def post(self, request, *args, **kwargs):
        code = request.POST.get("code", "").strip()
        lesson = Lesson.objects.filter(code=code).first()
        if not lesson:
            return JsonResponse({"error": "Урок не найден"}, status=404)
        return JsonResponse({"status": "ok", "url": f"/lessons/play/{code}/"})


class LessonSubmitView(LoginRequiredMixin, View):
    """
    API: принимает все ответы ученика сразу.
    Проверяет каждый блок, сохраняет Answer, обновляет LessonProgress,
    возвращает итог + (если разрешено) разбор ответов.
    """
    login_url = "accounts:auth"

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        lesson_id = data.get("lesson_id")
        answers = data.get("answers", {})  # {block_id: "answer"}

        lesson = get_object_or_404(Lesson, pk=lesson_id)
        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson,
        )

        # Проверка повторного прохождения
        if progress.is_finished and not lesson.allow_retry:
            return JsonResponse({
                "status": "error",
                "error": "Вы уже прошли этот урок",
            }, status=400)

        # Удаляем старые ответы (на случай перезапуска)
        Answer.objects.filter(user=request.user, block__lesson=lesson).delete()

        total_score = 0
        summary = []

        for block in lesson.blocks.all().order_by("order_index"):
            user_answer = (answers.get(str(block.id)) or "").strip()

            is_correct = False
            earned = 0

            if block.type == "translate":
                correct = block.config.get("correct", "").strip()
                is_correct = levenshtein_ratio(user_answer, correct) >= 0.8

            elif block.type == "audio":
                correct = block.config.get("correct", "").strip()
                is_correct = levenshtein_ratio(user_answer, correct) >= 0.8

            elif block.type == "quick":
                correct = block.config.get("correct", "").strip()
                is_correct = user_answer.lower() == correct.lower()

            elif block.type == "gap":
                correct = block.config.get("correct", "").strip()
                is_correct = user_answer.lower() == correct.lower()

            elif block.type == "build":
                correct = block.config.get("word", "").strip()
                is_correct = user_answer.lower() == correct.lower()

            elif block.type == "pairs":
                is_correct = self._check_pairs(
                    user_answer, block.config.get("pairs", []),
                )

            if is_correct:
                earned = block.points
                total_score += earned
                add_points(request.user, earned)

            Answer.objects.create(
                user=request.user,
                block=block,
                answer=user_answer,
                is_correct=is_correct,
                points_earned=earned,
            )

            summary.append({
                "block_id": block.id,
                "type": block.type,
                "type_display": block.get_type_display(),
                "user_answer": user_answer,
                "is_correct": is_correct,
                "points": earned,
                "max_points": block.points,
                "correct": block.config.get("correct", ""),
                "word": block.config.get("word", ""),
                "pairs": block.config.get("pairs", []),
            })

        # Завершаем прогресс
        progress.is_finished = True
        progress.finished_at = timezone.now()
        progress.score = total_score
        progress.save()

        update_streak(request.user)
        check_achievements(request.user)

        show_summary = lesson.show_answers_after

        return JsonResponse({
            "status": "ok",
            "score": total_score,
            "total_points": lesson.total_points(),
            "show_summary": show_summary,
            "summary": summary if show_summary else None,
        })

    def _check_pairs(self, user_answer, correct_pairs):
        """
        Проверяет связи ученика.
        user_answer — JSON-строка: '[["Китап","Книга"],["Өстәл","Стол"]]'
        correct_pairs — список списков: [["Китап","Книга"], ...]
        """
        try:
            user_pairs = json.loads(user_answer) if user_answer else []
        except (ValueError, TypeError):
            return False

        if not user_pairs or not correct_pairs:
            return False

        user_set = set()
        for p in user_pairs:
            if isinstance(p, list) and len(p) == 2:
                user_set.add((str(p[0]).strip(), str(p[1]).strip()))

        correct_set = set()
        for p in correct_pairs:
            if isinstance(p, list) and len(p) == 2:
                correct_set.add((str(p[0]).strip(), str(p[1]).strip()))

        return user_set == correct_set


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