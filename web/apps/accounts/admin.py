__all__ = ()

from apps.accounts.models import Notification, Profile

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from unfold.admin import ModelAdmin, StackedInline

admin.site.unregister(User)


class ProfileInline(StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "is_staff", "date_joined")
    compressed_fields = True
    warn_unsaved_form = True


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "profile", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "description")
