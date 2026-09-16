__all__ = ()

from ckeditor.fields import RichTextField

from django.db import models


class News(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Название",
    )
    text = RichTextField(
        verbose_name="Текст",
    )
    image = models.ImageField(
        upload_to="news/",
        blank=True,
        null=True,
        verbose_name="Картинка",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено",
    )

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
