from django.db import models

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
from apps.common.models.cta_section import AbstractCtaSectionModel
from apps.common.models.curators_section import AbstractCuratorsSectionModel


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
    slide = models.OneToOneField(
        HeroPromotionSlideModel,
        on_delete=models.CASCADE,
        related_name="card",
        null=True,
        blank=True,
        verbose_name="Слайд",
    )


class CuratorsSectionModel(AbstractCuratorsSectionModel):
    page = models.OneToOneField(
        LandyshevayaMainPageModel,
        on_delete=models.CASCADE,
        verbose_name="Привязка к странице",
    )


class CtaSectionModel(AbstractCtaSectionModel):
    page = models.OneToOneField(
        LandyshevayaMainPageModel,
        on_delete=models.CASCADE,
        verbose_name="Привязка к странице",
    )


class TitleDescriptionSlidersSectionModel(AbstractTitleDescriptionSlidersSectionModel):
    page = models.OneToOneField(
        LandyshevayaMainPageModel, on_delete=models.CASCADE, null=True, blank=True
    )


class TitleDescriptionSlideModel(AbstractTitleDescriptionSliderModel):
    section = models.ForeignKey(
        TitleDescriptionSlidersSectionModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )


class TitleDescriptionSlideGalleryModel(AbstractTitleDescriptionSliderGallery):
    slider = models.ForeignKey(
        TitleDescriptionSlideModel, on_delete=models.CASCADE, null=True, blank=True
    )


class OurWorkSectionModel(AbstractOurWorkSection):
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
