__all__ = ()

import json

from apps.generation.models import AIChatMessage
from apps.generation.services import (
    chat_with_tatar_ai,
    explain_tatar,
    generate_distractors,
    generate_lesson_blocks,
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
        ctx["chat_messages"] = AIChatMessage.objects.filter(
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

        history_qs = AIChatMessage.objects.filter(
            user=request.user,
        ).order_by("-created_at")[:10]
        history = [
            {"role": m.role, "content": m.content}
            for m in reversed(list(history_qs))
        ]

        user_msg = AIChatMessage.objects.create(
            user=request.user, role="user", content=message,
        )

        answer = chat_with_tatar_ai(history, message)
        if not answer:
            return JsonResponse(
                {"error": "ИИ недоступен. Попробуйте ещё раз."},
                status=502,
            )

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
# ГЕНЕРАЦИЯ СЛОВ — доступно всем авторизованным
# ══════════════════════════════════════════════════════════════════

class GenerateWordsView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат"}, status=400)

        theme = data.get("theme", "family")
        try:
            n = min(int(data.get("n", 5)), 20)
        except (TypeError, ValueError):
            n = 5

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
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат"}, status=400)

        correct = (data.get("correct") or "").strip()
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
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат"}, status=400)

        question = (data.get("question") or "").strip()
        if not question:
            return JsonResponse({"error": "Пустой вопрос"}, status=400)

        answer = explain_tatar(question)
        if not answer:
            return JsonResponse({"error": "ИИ недоступен"}, status=502)

        return JsonResponse({"status": "ok", "answer": answer})


# ══════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ БЛОКОВ УРОКА — доступно всем авторизованным
# ══════════════════════════════════════════════════════════════════

class GenerateLessonBlocksView(LoginRequiredMixin, View):
    login_url = "accounts:auth"

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат"}, status=400)

        theme = (data.get("theme") or "").strip()
        if not theme:
            return JsonResponse({"error": "Укажите тему"}, status=400)

        types = data.get("types") or ["translate", "build"]
        try:
            count = int(data.get("count", 8))
        except (TypeError, ValueError):
            count = 8
        use_dictionary = bool(data.get("use_dictionary", True))

        blocks = generate_lesson_blocks(
            theme=theme,
            types=types,
            count=count,
            use_dictionary=use_dictionary,
        )

        if not blocks:
            return JsonResponse(
                {"error": "Не удалось сгенерировать блоки. Попробуйте другую тему."},
                status=502,
            )

        return JsonResponse({
            "status": "ok",
            "blocks": blocks,
            "count": len(blocks),
        })
