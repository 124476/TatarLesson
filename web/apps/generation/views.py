__all__ = ()

import json

from apps.generation.models import AIChatMessage
from apps.generation.services import (
    chat_with_tatar_ai,
    explain_tatar,
    generate_competition_tasks,
    generate_distractors,
    generate_words,
)
from apps.words.models import Word

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView


# ══════════════════════════════════════════════════════════════════
# AI-ЧАТ
# ══════════════════════════════════════════════════════════════════

class AIChatView(LoginRequiredMixin, TemplateView):
    template_name = "generation/chat.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["messages"] = AIChatMessage.objects.filter(
            user=self.request.user,
        ).order_by("created_at")
        return ctx


class AIChatSendView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат"}, status=400)

        message = (data.get("message") or "").strip()
        if not message:
            return JsonResponse({"error": "Пустое сообщение"}, status=400)
        if len(message) > 500:
            return JsonResponse({"error": "Слишком длинное (макс. 500)"}, status=400)

        # История
        history_qs = AIChatMessage.objects.filter(
            user=request.user,
        ).order_by("-created_at")[:10]
        history = [
            {"role": m.role, "content": m.content}
            for m in reversed(list(history_qs))
        ]

        # Сохраняем сообщение пользователя
        user_msg = AIChatMessage.objects.create(
            user=request.user, role="user", content=message,
        )

        # Спрашиваем LLM
        answer = chat_with_tatar_ai(history, message)
        if not answer:
            return JsonResponse(
                {"error": "ИИ недоступен. Попробуйте ещё раз."},
                status=502,
            )

        # Сохраняем ответ
        assistant_msg = AIChatMessage.objects.create(
            user=request.user, role="assistant", content=answer,
        )

        return JsonResponse({
            "status": "ok",
            "user_message_id": user_msg.id,
            "answer": answer,
            "answer_id": assistant_msg.id,
        })


class AIChatClearView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        AIChatMessage.objects.filter(user=request.user).delete()
        return JsonResponse({"status": "ok"})


# ══════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ СЛОВ
# ══════════════════════════════════════════════════════════════════

class GenerateWordsView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        if not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)

        data = json.loads(request.body)
        theme = data.get("theme", "family")
        n = min(int(data.get("n", 5)), 20)

        words = generate_words(theme=theme, n=n)
        if not words:
            return JsonResponse(
                {"error": "Не удалось сгенерировать. Попробуйте ещё раз."},
                status=502,
            )

        return JsonResponse({"status": "ok", "words": words, "count": len(words)})


class GenerateDistractorsView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        if not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)

        data = json.loads(request.body)
        correct = data.get("correct", "").strip()
        theme = data.get("theme", "общее")

        if not correct:
            return JsonResponse({"error": "Укажите правильный ответ"}, status=400)

        options = generate_distractors(correct=correct, theme=theme)
        if not options:
            return JsonResponse({"error": "Не удалось"}, status=502)

        return JsonResponse({"status": "ok", "options": options})


class ExplainView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        data = json.loads(request.body)
        question = data.get("question", "").strip()

        if not question:
            return JsonResponse({"error": "Пустой вопрос"}, status=400)

        answer = explain_tatar(question)
        if not answer:
            return JsonResponse({"error": "ИИ недоступен"}, status=502)

        return JsonResponse({"status": "ok", "answer": answer})


# ══════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ ЗАДАЧ СОРЕВНОВАНИЯ
# ══════════════════════════════════════════════════════════════════

class GenerateCompetitionTasksView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        if not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)

        data = json.loads(request.body)
        theme = (data.get("theme") or "").strip()
        n_tasks = min(int(data.get("n_tasks", 5)), 15)
        task_types = data.get("task_types") or ["text", "choice", "build"]
        use_dictionary = data.get("use_dictionary", True)

        if not theme:
            return JsonResponse({"error": "Укажите тему"}, status=400)

        # Слова: либо из словаря, либо генерируем
        words = None
        if use_dictionary:
            # Пробуем найти слова по теме в БД
            db_words = list(
                Word.objects
                .filter(Q(theme=theme) | Q(russian__icontains=theme))
                .values("tatar", "russian")[:20]
            )
            if len(db_words) >= 5:
                words = db_words

        tasks = generate_competition_tasks(
            theme=theme,
            n_tasks=n_tasks,
            task_types=task_types,
            words=words,
        )

        if not tasks:
            return JsonResponse(
                {"error": "Не удалось сгенерировать задачи. Попробуйте ещё раз."},
                status=502,
            )

        return JsonResponse({
            "status": "ok",
            "tasks": tasks,
            "count": len(tasks),
        })
