from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.mixins import ImageVariantsMixin


class AbstractCuratorsSectionModel(ImageVariantsMixin, models.Model):
    """Секция кураторов"""

    poster = models.ImageField(
        upload_to="main-page/curators-section/",
        blank=True,
        verbose_name="Изображение кураторов",
    )
    poster_mobile = models.ImageField(
        upload_to="main-page/curators-section/",
        blank=True,
        verbose_name="Изображение кураторов (мобильная версия)",
    )
    title = models.CharField(
        max_length=255, verbose_name="Заголовок секции", blank=True, null=True
    )
    description = models.TextField(
        verbose_name="Описание секции",
        help_text="Идет после контента",
        null=True,
        blank=True,
    )
    content = CKEditor5Field(
        config_name="blog_content", verbose_name="Контент", null=True, blank=True
    )

    IMAGE_VARIANT_FIELDS = ["poster", "poster_mobile"]

    class Meta:
        abstract = True
        verbose_name = "Секция «Кураторы»"
        verbose_name_plural = "Секция «Кураторы»"

    def __str__(self):
        return "Секция «Кураторы»"
