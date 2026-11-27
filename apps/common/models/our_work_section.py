from django.db import models

from apps.common.mixins import ImageVariantsMixin


class AbstractOurWorkImageGallery(models.Model, ImageVariantsMixin):
    IMAGE_SIZE_VARIANTS = {
        "standard": "Стандартное (маленькое)",
        "big": "Вытянутое (вертикальное)",
    }

    poster = models.ImageField(
        upload_to="main-page/our-work/",
        blank=True,
        verbose_name="Изображение «Наши работы»",
    )
    poster_mobile = models.ImageField(
        upload_to="main-page/our-work/",
        blank=True,
        verbose_name="Изображение «Наши работы» (мобильная версия)",
    )
    size = models.CharField(
        max_length=32,
        verbose_name="Размер обертки изображения",
        choices=IMAGE_SIZE_VARIANTS,
        default=IMAGE_SIZE_VARIANTS["standard"],
    )

    class Meta:
        abstract = True
        verbose_name = "Изображение «Наши работы»"
        verbose_name = "Изображения «Наши работы»"


class AbstractOurWorkSection(models.Model):
    title = models.CharField(
        max_length=255, verbose_name="Заголовок секции", blank=True, null=True
    )

    class Meta:
        abstract = True
        verbose_name = "Секция «Наши работы»"
        verbose_name = "Секция «Наши работы»"
