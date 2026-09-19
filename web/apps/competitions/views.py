__all__ = ()

import json

from apps.competitions.models import (
    Competition, CompetitionParticipant, CompetitionTask, Submission,
)
from apps.gamification.services import (
    add_points, check_achievements, levenshtein_ratio, update_streak,
)
from apps.lessons.api import TatSoftAPI
from apps.words.models import Word

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Max, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.generic import TemplateView


# ==================== ХЕЛПЕРЫ ПРОВЕРКИ ====================

def check_text_answer(user_answer, correct):
    correct = str(correct or "").strip()
    user_answer = str(user_answer or "").strip()
    if not correct:
        return False
    threshold = 0.8 if len(correct) > 4 else 0.95
    return levenshtein_ratio(user_answer, correct) >= threshold


def check_choice(user_answer, options):
    if not isinstance(options, list):
        return False
    correct = next(
        (str(o.get("text", "")).strip() for o in options if o.get("is_correct")),
        "",
    )
    return bool(correct) and user_answer.strip().lower() == correct.lower()


def check_multiple_choice(user_answer_list, options):
    if not isinstance(user_answer_list, list) or not isinstance(options, list):
        return False
    correct_set = {
        str(o.get("text", "")).strip().lower()
        for o in options if o.get("is_correct")
    }
    user_set = {str(a).strip().lower() for a in user_answer_list}
    return user_set == correct_set and len(correct_set) > 0


def check_build(user_answer, build_word):
    return str(user_answer or "").strip().lower() == str(build_word or "").strip().lower()


def check_pairs(user_answer_json, correct_pairs):
    try:
        user_pairs = json.loads(user_answer_json) if user_answer_json else []
    except (ValueError, TypeError):
        return False

    if not isinstance(user_pairs, list) or not isinstance(correct_pairs, list):
        return False
    if not user_pairs or not correct_pairs:
        return False

    user_set = {
        (str(p[0]).strip().lower(), str(p[1]).strip().lower())
        for p in user_pairs
        if isinstance(p, list) and len(p) == 2
    }
    correct_set = {
        (str(p[0]).strip().lower(), str(p[1]).strip().lower())
        for p in correct_pairs
        if isinstance(p, list) and len(p) == 2
    }
    return user_set == correct_set and len(correct_set) > 0


def check_voice(user_answer, expected):
    expected = str(expected or "").strip()
    user_answer = str(user_answer or "").strip()
    if not expected or not user_answer:
        return False
    return levenshtein_ratio(user_answer, expected) >= 0.7


# ==================== ПУБЛИЧНЫЕ СТРАНИЦЫ ====================

class CompetitionListView(TemplateView):
    template_name = "competitions/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Competition.objects.filter(is_published=True)
        now = timezone.now()
        ctx["running"] = qs.filter(
            start_time__lte=now, end_time__gte=now,
        ).order_by("end_time")
        ctx["upcoming"] = qs.filter(start_time__gt=now).order_by("start_time")
        ctx["finished"] = qs.filter(end_time__lt=now).order_by("-end_time")[:20]
        return ctx


class CompetitionDetailView(TemplateView):
    """Единый шаблон: список задач + выбранная задача + мои посылки + положение."""
    template_name = "competitions/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        competition = get_object_or_404(
            Competition, pk=self.kwargs["pk"], is_published=True,
        )
        ctx["competition"] = competition
        ctx["status"] = competition.get_status()

        if self.request.user.is_authenticated and competition.is_running():
            CompetitionParticipant.objects.get_or_create(
                competition=competition, user=self.request.user,
            )

        tasks = list(competition.tasks.all().order_by("order_index"))
        ctx["tasks"] = tasks if not competition.is_upcoming() else []

        # Мои посылки по всему соревнованию
        if self.request.user.is_authenticated:
            ctx["my_submissions"] = (
                Submission.objects
                .filter(user=self.request.user, task__competition=competition)
                .select_related("task")
                .order_by("-created_at")
            )
            participant = CompetitionParticipant.objects.filter(
                competition=competition, user=self.request.user,
            ).first()
            ctx["my_score"] = participant.score if participant else 0
        else:
            ctx["my_submissions"] = []
            ctx["my_score"] = 0

        # Выбранная задача (из URL или GET)
        task_id = self.kwargs.get("task_id") or self.request.GET.get("task")
        selected_task = None
        if task_id:
            selected_task = competition.tasks.filter(pk=task_id).first()
        ctx["selected_task"] = selected_task

        if selected_task:
            if self.request.user.is_authenticated:
                task_subs = (
                    Submission.objects
                    .filter(user=self.request.user, task=selected_task)
                    .order_by("-created_at")
                )
                ctx["task_my_submissions"] = task_subs
                ctx["attempts_left"] = max(0, selected_task.max_attempts - task_subs.count())
            else:
                ctx["task_my_submissions"] = []
                ctx["attempts_left"] = selected_task.max_attempts
        else:
            ctx["task_my_submissions"] = []
            ctx["attempts_left"] = 0

        # Лидерборд
        if competition.is_upcoming():
            ctx["leaderboard"] = []
            ctx["standings_rows"] = []
            return ctx

        leaderboard = list(
            CompetitionParticipant.objects
            .filter(competition=competition)
            .select_related("user")
            .order_by("-score", "created_at")[:100]
        )
        ctx["leaderboard"] = leaderboard

        # ── Матрица результатов ──
        # Лучшие правильные посылки по (user, task)
        best = {}
        correct_qs = (
            Submission.objects
            .filter(task__competition=competition, is_correct=True)
            .values("user_id", "task_id", "points_earned")
        )
        for s in correct_qs:
            key = (s["user_id"], s["task_id"])
            if key not in best or s["points_earned"] > best[key]:
                best[key] = s["points_earned"]

        # Количество неверных посылок по (user, task)
        wrong_qs = (
            Submission.objects
            .filter(task__competition=competition, is_correct=False)
            .values("user_id", "task_id")
            .annotate(n=Count("id"))
        )
        wrong = {(s["user_id"], s["task_id"]): s["n"] for s in wrong_qs}

        standings_rows = []
        for p in leaderboard:
            row = {"user": p.user, "score": p.score, "tasks": []}
            for task in tasks:
                key = (p.user_id, task.id)
                if key in best:
                    row["tasks"].append({
                        "task_id": task.id,
                        "status": "solved",
                        "points": best[key],
                        "wrong": wrong.get(key, 0),
                    })
                elif key in wrong:
                    row["tasks"].append({
                        "task_id": task.id,
                        "status": "attempted",
                        "points": 0,
                        "wrong": wrong[key],
                    })
                else:
                    row["tasks"].append({
                        "task_id": task.id,
                        "status": "none",
                        "points": 0,
                        "wrong": 0,
                    })
            standings_rows.append(row)

        ctx["standings_rows"] = standings_rows
        return ctx


class CompetitionTaskView(CompetitionDetailView):
    """Тот же detail, но с task_id из URL → selected_task заполнится автоматически."""
    pass


# ==================== ОТПРАВКА РЕШЕНИЯ ====================

class SubmitSolutionView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    PENALTY_PER_ATTEMPT = 0.2
    MIN_FACTOR = 0.2

    def post(self, request, *args, **kwargs):
        task = get_object_or_404(CompetitionTask, pk=self.kwargs["task_id"])
        competition = task.competition

        if not competition.is_running():
            return JsonResponse(
                {"status": "error", "error": "Соревнование не идёт"},
                status=400,
            )

        attempts = Submission.objects.filter(user=request.user, task=task).count()
        if attempts >= task.max_attempts:
            return JsonResponse(
                {"status": "error", "error": "Исчерпаны попытки"},
                status=400,
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "error": "Неверный формат данных"},
                status=400,
            )

        answer = data.get("answer")

        is_correct = False
        answer_str = ""

        if task.task_type == "multiple_choice":
            if not isinstance(answer, list):
                return JsonResponse(
                    {"status": "error", "error": "Ожидался список вариантов"},
                    status=400,
                )
            is_correct = check_multiple_choice(answer, task.options)
            answer_str = json.dumps(answer, ensure_ascii=False)

        elif task.task_type == "choice":
            is_correct = check_choice(str(answer or ""), task.options)
            answer_str = str(answer or "")

        elif task.task_type == "build":
            is_correct = check_build(str(answer or ""), task.build_word)
            answer_str = str(answer or "")

        elif task.task_type == "pairs":
            is_correct = check_pairs(str(answer or ""), task.pairs)
            answer_str = str(answer or "")

        elif task.task_type == "voice":
            expected = (task.voice_text or "").strip() or (task.correct_answer or "").strip()
            if not expected:
                return JsonResponse(
                    {"status": "error", "error": "Задача настроена неверно"},
                    status=400,
                )
            is_correct = check_voice(str(answer or ""), expected)
            answer_str = str(answer or "")

        else:
            is_correct = check_text_answer(str(answer or ""), task.correct_answer)
            answer_str = str(answer or "")

        # ── Уже решал эту задачу раньше? ──
        already_solved = Submission.objects.filter(
            user=request.user, task=task, is_correct=True,
        ).exists()

        # ── Очки ──
        if is_correct and not already_solved:
            # Первая правильная посылка — применяем штраф за количество
            # предыдущих НЕВЕРНЫХ попыток. (attempts = все посылки до этой)
            factor = max(
                self.MIN_FACTOR,
                1.0 - self.PENALTY_PER_ATTEMPT * attempts,
            )
            points = int(round(task.points * factor))
        else:
            # Неверная или повторная правильная — 0 новых баллов
            points = 0

        Submission.objects.create(
            user=request.user,
            task=task,
            answer=answer_str,
            is_correct=is_correct,
            points_earned=points,
            attempt_number=attempts + 1,
        )

        participant, _ = CompetitionParticipant.objects.get_or_create(
            competition=competition, user=request.user,
        )
        participant.score = self._calc_score(request.user, competition)
        participant.save()

        if is_correct and not already_solved:
            add_points(request.user, points)
            update_streak(request.user)
            check_achievements(request.user)

        return JsonResponse({
            "status": "ok",
            "is_correct": is_correct,
            "points": points,
            "already_solved": already_solved,
            "attempts_left": task.max_attempts - (attempts + 1),
            "message": "Верно!" if is_correct else "Неверно",
        })

    def _calc_score(self, user, competition):
        results = (
            Submission.objects
            .filter(user=user, task__competition=competition)
            .values("task")
            .annotate(best=Max("points_earned"))
        )
        return sum(r["best"] or 0 for r in results)


# ==================== API ДЛЯ ГОЛОСА ====================

class CompetitionSynthesizeView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def get(self, request, *args, **kwargs):
        text = request.GET.get("text", "").strip()
        if not text:
            return JsonResponse({"error": "no text"}, status=400)
        audio = TatSoftAPI.synthesize(text)
        if not audio:
            return JsonResponse({"error": "tts failed"}, status=502)
        return HttpResponse(audio, content_type="audio/wav")


class CompetitionRecognizeView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request, *args, **kwargs):
        audio = request.FILES.get("audio")
        if not audio:
            return JsonResponse({"error": "no audio"}, status=400)
        text = TatSoftAPI.recognize(audio.read())
        return JsonResponse({"text": text or ""})


# ==================== АДМИН ====================

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "accounts:auth"

    def test_func(self):
        return self.request.user.is_staff


class CompetitionAdminListView(AdminRequiredMixin, TemplateView):
    template_name = "competitions/admin_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["competitions"] = Competition.objects.all().order_by("-start_time")
        return ctx


class CompetitionAdminCreateView(AdminRequiredMixin, TemplateView):
    template_name = "competitions/admin_create.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cid = self.kwargs.get("pk")

        tasks_json = []
        ctx["is_edit"] = False

        if cid:
            competition = get_object_or_404(Competition, pk=cid)
            ctx["competition"] = competition
            ctx["is_edit"] = True
            tasks_json = [
                {
                    "title": t.title,
                    "statement": t.statement,
                    "task_type": t.task_type,
                    "correct_answer": t.correct_answer,
                    "options": t.options,
                    "build_word": t.build_word,
                    "build_hint": t.build_hint,
                    "pairs": t.pairs,
                    "voice_text": t.voice_text,
                    "points": t.points,
                    "max_attempts": t.max_attempts,
                }
                for t in competition.tasks.all().order_by("order_index")
            ]

        ctx["tasks_json"] = tasks_json
        return ctx


class CompetitionAdminSaveView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "error": "Неверный формат данных"},
                status=400,
            )

        cid = data.get("competition_id")
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        start_time = (data.get("start_time") or "").strip()
        end_time = (data.get("end_time") or "").strip()
        is_published = data.get("is_published", False)
        tasks_data = data.get("tasks", [])

        if not title or not start_time or not end_time:
            return JsonResponse(
                {"status": "error", "error": "Заполните название и время"},
                status=400,
            )

        start_dt = parse_datetime(start_time)
        end_dt = parse_datetime(end_time)
        if not start_dt or not end_dt or end_dt <= start_dt:
            return JsonResponse(
                {"status": "error", "error": "Неверное время"},
                status=400,
            )

        if cid:
            competition = get_object_or_404(Competition, pk=cid)

            if competition.start_time <= timezone.now():
                return JsonResponse(
                    {
                        "status": "error",
                        "error": "Нельзя редактировать соревнование после старта",
                    },
                    status=400,
                )

            competition.title = title
            competition.description = description
            competition.start_time = start_dt
            competition.end_time = end_dt
            competition.is_published = is_published
            competition.save()
            competition.tasks.all().delete()
        else:
            competition = Competition.objects.create(
                title=title,
                description=description,
                start_time=start_dt,
                end_time=end_dt,
                is_published=is_published,
                created_by=request.user,
            )

        created_count = 0
        for i, t in enumerate(tasks_data):
            title_t = (t.get("title") or "").strip()
            statement = (t.get("statement") or "").strip()
            task_type = t.get("task_type", "text")

            if not title_t or not statement:
                continue

            if task_type in ("text", "voice"):
                if not (t.get("correct_answer") or "").strip():
                    continue
                if task_type == "voice" and not (
                    (t.get("voice_text") or "").strip()
                    or (t.get("correct_answer") or "").strip()
                ):
                    continue

            elif task_type in ("choice", "multiple_choice"):
                options = t.get("options", [])
                if not isinstance(options, list):
                    continue
                if not any(o.get("is_correct") for o in options):
                    continue

            elif task_type == "build":
                if not (t.get("build_word") or "").strip():
                    continue

            elif task_type == "pairs":
                pairs = t.get("pairs", [])
                if not isinstance(pairs, list) or len(pairs) < 2:
                    continue

            CompetitionTask.objects.create(
                competition=competition,
                title=title_t,
                statement=statement,
                task_type=task_type,
                correct_answer=t.get("correct_answer", ""),
                options=t.get("options", []),
                build_word=t.get("build_word", ""),
                build_hint=t.get("build_hint", ""),
                pairs=t.get("pairs", []),
                voice_text=t.get("voice_text", ""),
                points=int(t.get("points", 100)),
                max_attempts=int(t.get("max_attempts", 5)),
                order_index=created_count,
            )
            created_count += 1

        return JsonResponse({
            "status": "ok",
            "competition_id": competition.id,
            "tasks_created": created_count,
        })


class CompetitionAdminDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        competition = get_object_or_404(Competition, pk=pk)
        competition.delete()
        return JsonResponse({"status": "ok"})


class CompetitionWordsAPIView(AdminRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        q = (request.GET.get("q") or "").strip().lower()
        qs = Word.objects.all().order_by("tatar")
        if q:
            qs = [
                w for w in qs
                if q in w.tatar.lower() or q in w.russian.lower()
            ]

        return JsonResponse({
            "words": [
                {
                    "id": w.id,
                    "tatar": w.tatar,
                    "russian": w.russian,
                    "transcription": w.transcription,
                    "theme": w.theme,
                    "theme_display": w.theme_display,
                }
                for w in qs
            ]
        })