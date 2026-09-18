__all__ = ()

from apps.competitions.models import (
    Competition, CompetitionParticipant, CompetitionTask, Submission,
)

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline


class CompetitionTaskInline(TabularInline):
    model = CompetitionTask
    extra = 1
    fields = ("order_index", "title", "task_type", "points", "max_attempts")
    show_change_link = True


@admin.register(Competition)
class CompetitionAdmin(ModelAdmin):
    list_display = ("title", "start_time", "end_time", "is_published", "get_status")
    list_filter = ("is_published", "start_time")
    search_fields = ("title", "description")
    inlines = [CompetitionTaskInline]
    date_hierarchy = "start_time"
    compressed_fields = True

    def get_status(self, obj):
        return {"upcoming": "⏳", "running": "🟢", "finished": "✅"}.get(obj.get_status(), "—")
    get_status.short_description = "Статус"


@admin.register(CompetitionTask)
class CompetitionTaskAdmin(ModelAdmin):
    list_display = ("title", "competition", "task_type", "points", "max_attempts")
    list_filter = ("competition", "task_type")
    search_fields = ("title", "statement")


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ("user", "task", "is_correct", "points_earned", "attempt_number", "created_at")
    list_filter = ("is_correct", "task__competition")
    readonly_fields = ("user", "task", "answer", "is_correct", "points_earned", "attempt_number")


@admin.register(CompetitionParticipant)
class ParticipantAdmin(ModelAdmin):
    list_display = ("user", "competition", "score")
    list_filter = ("competition",)