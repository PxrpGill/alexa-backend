from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.mixins import ImageVariantsMixin


class AbstractTitleDescriptionSliderGallery(ImageVariantsMixin, models.Model):
    poster = models.ImageField(
        upload_to="main-page/title-description-slider/",
        blank=True,
        verbose_name="Изображение слайда «Преимуществ»",
    )
    poster_mobile = models.ImageField(
        upload_to="main-page/title-description-slider/",
        blank=True,
        verbose_name="Изображение слайда «Преимуществ» (мобильная версия)",
    )

    class Meta:
        abstract = True
        verbose_name = "Изображение слайда «Преимуществ»"
        verbose_name_plural = "Изображение слайда «Преимуществ»"

    def __str__(self):
        return "Изображение слайда «Преимуществ»"


class AbstractTitleDescriptionSliderModel(models.Model):
    title = models.CharField(
        max_length=255, verbose_name="Заголовок слайдера", blank=True, null=True
    )
    description = CKEditor5Field(
        config_name="blog_content",
        verbose_name="Описание слайдера",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True
        verbose_name = "Слайдер «Наши преимущества»"
        verbose_name_plural = "Слайдер «Наши преимущества»"

    def __str__(self):
        return self.title or "Слайдер «Наши преимущества»"


class AbstractTitleDescriptionSlidersSectionModel(models.Model):
    title = models.CharField(
        max_length=255, verbose_name="Заголовок секции", blank=True, null=True
    )

    class Meta:
        abstract = True
        verbose_name = "Секция слайдеров «Наши преимущества»"
        verbose_name_plural = "Секция слайдеров «Наши преимущества»"

    def __str__(self):
        return self.title or "Секция слайдеров «Наши преимущества»"
