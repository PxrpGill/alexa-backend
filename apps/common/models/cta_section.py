from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class AbstractCtaSectionModel(models.Model):
    """CTA секция"""

    title = CKEditor5Field(
        config_name="blog_content", verbose_name="Заголовок", null=True, blank=True
    )
    description = CKEditor5Field(
        config_name="blog_content", verbose_name="Описание", null=True, blank=True
    )

    class Meta:
        abstract = True
        verbose_name = "CTA"
        verbose_name_plural = "CTA"

    def __str__(self):
        return "Контент CTA"
