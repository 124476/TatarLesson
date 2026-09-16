__all__ = ()

from apps.gamification.models import Duel
from apps.lessons.models import Answer

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView, TemplateView


class LeaderboardView(LoginRequiredMixin, ListView):
    template_name = "gamification/leaderboard.html"
    context_object_name = "leaders"
    login_url = "accounts:auth"

    def get_queryset(self):
        class_id = self.request.GET.get("class_id")
        qs = User.objects.filter(is_staff=False)
        if class_id:
            qs = qs.filter(profile__class_group_id=class_id)
        return qs.order_by("-profile__points")[:50]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["my_points"] = self.request.user.profile.points
        ctx["my_streak"] = self.request.user.profile.streak
        return ctx


class DuelCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        opponent_id = request.POST.get("opponent_id")
        opponent = get_object_or_404(User, pk=opponent_id)
        if opponent == request.user:
            return JsonResponse({"error": "Нельзя вызвать себя"}, status=400)
        duel = Duel.objects.create(
            player1=request.user, player2=opponent,
        )
        return JsonResponse({"status": "ok", "duel_id": duel.id})


class DuelView(LoginRequiredMixin, TemplateView):
    template_name = "gamification/duel.html"
    login_url = "accounts:auth"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["duel"] = get_object_or_404(Duel, pk=self.kwargs["pk"])
        return ctx


class DuelFinishView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        import json
        data = json.loads(request.body)
        duel = get_object_or_404(Duel, pk=data["duel_id"])
        duel.score1 = data.get("score1", 0)
        duel.score2 = data.get("score2", 0)
        duel.is_finished = True
        if duel.score1 > duel.score2:
            duel.winner = duel.player1
        elif duel.score2 > duel.score1:
            duel.winner = duel.player2
        duel.save()
        return JsonResponse({"status": "ok", "winner": duel.winner.username if duel.winner else None})

class TopUsersAPI(View):
    def get(self, request):
        users = User.objects.filter(is_staff=False).order_by("-profile__points")[:5]
        return JsonResponse({
            "users": [
                {"username": u.username, "points": u.profile.points}
                for u in users
            ]
        })