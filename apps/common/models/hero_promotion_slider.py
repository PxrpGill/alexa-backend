from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.mixins import ImageVariantsMixin


class AbstractHeroSlideDescriptionCard(models.Model):
    title = models.TextField(verbose_name="Заголовок", blank=True, null=True)
    content = CKEditor5Field(
        config_name="blog_content", verbose_name="Контент", null=True, blank=True
    )

    def __str__(self):
        return self.title or "Карточка слайда"

    class Meta:
        abstract = True
        verbose_name = "Карточка слайда"
        verbose_name_plural = "Карточки слайда"


class AbstractHeroPromotionSlideModel(ImageVariantsMixin, models.Model):
    SLIDE_TEXT_THEME_VARIANTS = (
        ("light", "Светлая тема"),
        ("dark", "Тёмная тема"),
    )

    title = models.CharField(
        max_length=255, verbose_name="Заголовок слайда", null=True, blank=True
    )
    subtitle = models.CharField(
        max_length=255, verbose_name="Надзаголовок слайда", null=True, blank=True
    )
    legend = models.CharField(
        max_length=255, verbose_name="Подзаголовок слайда", null=True, blank=True
    )
    poster = models.ImageField(
        upload_to="hero-promotion-slides-backgrounds/",
        blank=True,
        null=True,
        verbose_name="Фон слайда",
    )
    poster_mobile = models.ImageField(
        upload_to="hero-promotion-slides-backgrounds/",
        blank=True,
        null=True,
        verbose_name="Фон слайда (мобильная версия)",
    )
    text_theme = models.CharField(
        max_length=5,
        choices=SLIDE_TEXT_THEME_VARIANTS,
        default="light",
        verbose_name="Тема текста",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title or "Слайд"

    class Meta:
        abstract = True
        verbose_name = "Слайд акции"
        verbose_name_plural = "Слайды акции"
