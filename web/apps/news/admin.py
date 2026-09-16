__all__ = ()

from apps.news.models import News

from django.contrib import admin

from unfold.admin import ModelAdmin


@admin.register(News)
class NewsAdmin(ModelAdmin):
    list_display = ["title", "created_at", "updated_at"]
    search_fields = ["title"]
    compressed_fields = True
