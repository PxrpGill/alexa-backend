from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.mixins import ImageVariantsMixin
from apps.common.models import SingletonModel
from apps.common.models.hero_promotion_slider import (
    AbstractHeroPromotionSlideModel,
    AbstractHeroSlideDescriptionCard,
)
from apps.common.models.title_description_slider import (
    AbstractTitleDescriptionSliderGallery,
    AbstractTitleDescriptionSliderModel,
    AbstractTitleDescriptionSlidersSectionModel,
)
from apps.common.models.our_work_section import (
    AbstractOurWorkImageGallery,
    AbstractOurWorkSection,
)
from apps.common.models.faq_section import AbstractFaqFactoids, AbstractFaqSection


class LandyshevayaMainPageModel(SingletonModel):
    """Главная страница филиала Ландышевая (ровно одна запись)"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Главная страница филиала Ландышевая"
        verbose_name_plural = "Главная страница филиала Ландышевая"

    def __str__(self):
        return "Главная страница (Ландышевая)"


class HeroPromotionSlideModel(AbstractHeroPromotionSlideModel):
    """Слайд hero-слайдера главной страницы."""

    page = models.ForeignKey(
        LandyshevayaMainPageModel,
        on_delete=models.CASCADE,
        related_name="hero_slides",
        verbose_name="Страница",
    )
    position = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name="Порядок показа",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Показывать слайд",
    )

    IMAGE_VARIANT_FIELDS = ["poster", "poster_mobile"]

    class Meta(AbstractHeroPromotionSlideModel.Meta):
        ordering = ("position", "id")
        verbose_name = "Слайд главной страницы"
        verbose_name_plural = "Слайды главной страницы"

    def __str__(self):
        return self.title or f"Слайд #{self.position}"


class HeroPromotionSlideDescriptionCard(AbstractHeroSlideDescriptionCard):
    """Карточка-плашка, которая лежит поверх слайда."""

    BUTTON_TARGET_VARIANTS = (
        ("_self", "В текущем окне"),
        ("_blank", "В новом окне"),
    )

    slide = models.OneToOneField(
        HeroPromotionSlideModel,
        on_delete=models.CASCADE,
        related_name="card",
        null=True,
        blank=True,
        verbose_name="Слайд",
    )
    button_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Текст кнопки",
    )
    button_href = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Ссылка кнопки",
    )
    button_target = models.CharField(
        max_length=6,
        choices=BUTTON_TARGET_VARIANTS,
        default="_self",
        blank=True,
        verbose_name="Открывать кнопку",
    )
    is_open_feedback_modal = models.BooleanField(
        default=False,
        verbose_name="Кнопка открывает форму записи",
    )

    class Meta(AbstractHeroSlideDescriptionCard.Meta):
        verbose_name = "Карточка слайда"
        verbose_name_plural = "Карточки слайдов"

    def __str__(self):
        return self.title or "Карточка слайда"


class CuratorsSectionModel(models.Model, ImageVariantsMixin):
    """Секция кураторов"""

    poster = models.ImageField(
        upload_to="main-page/curators-section/", blank=True, verbose_name="Баннер"
    )
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
        verbose_name="Описание секции", help_text="Идет после контента"
    )
    content = CKEditor5Field(config_name="blog_content", verbose_name="Контент")

    IMAGE_VARIANT_FIELDS = ["poster", "poster_mobile"]

    page = models.OneToOneField(
        LandyshevayaMainPageModel,
        on_delete=models.CASCADE,
        verbose_name="Привязка к странице",
    )

    class Meta:
        verbose_name = "Секция «Кураторы»"
        verbose_name_plural = "Секция «Кураторы»"

    def __str__():
        return "Секция «Кураторы»"


class CtaSectionModel(models.Model):
    """CTA секция"""

    title = CKEditor5Field(config_name="blog_content", verbose_name="Заголовок")
    description = CKEditor5Field(config_name="blog_content", verbose_name="Описание")

    page = models.OneToOneField(
        LandyshevayaMainPageModel,
        on_delete=models.CASCADE,
        verbose_name="Привязка к странице",
    )

    class Meta:
        verbose_name = "CTA"
        verbose_name_plural = "CTA"

    def __str__(self):
        return "Контент CTA"


class TitleDescriptionSlidersSectionModel(AbstractTitleDescriptionSlidersSectionModel):
    """Секция слайдеров «Наши преимущества»"""

    page = models.OneToOneField(
        LandyshevayaMainPageModel, on_delete=models.CASCADE, null=True, blank=True
    )


class TitleDescriptionSlideModel(AbstractTitleDescriptionSliderModel):
    """Слайдер «Наши преимущества»"""

    section = models.ForeignKey(
        TitleDescriptionSlidersSectionModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )


class TitleDescriptionSlideGalleryModel(AbstractTitleDescriptionSliderGallery):
    """Галерея изображений слайдера «Наши преимущества»"""

    slider = models.ForeignKey(
        TitleDescriptionSlideModel, on_delete=models.CASCADE, null=True, blank=True
    )


class OurWorkSectionModel(AbstractOurWorkSection):
    """Секция «Наши работы»"""

    page = models.OneToOneField(
        LandyshevayaMainPageModel, on_delete=models.CASCADE, null=True, blank=True
    )


class OurWorkImageGalleryModel(AbstractOurWorkImageGallery):
    section = models.ForeignKey(
        OurWorkSectionModel, on_delete=models.CASCADE, null=True, blank=True
    )


class FaqSectionModel(AbstractFaqSection):
    page = models.OneToOneField(
        LandyshevayaMainPageModel, on_delete=models.CASCADE, null=True, blank=True
    )


class FaqFactoidsModel(AbstractFaqFactoids):
    section = models.ForeignKey(
        FaqSectionModel, on_delete=models.CASCADE, null=True, blank=True
    )
