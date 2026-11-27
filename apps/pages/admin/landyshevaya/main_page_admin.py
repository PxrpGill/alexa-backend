from django.contrib import admin
from nested_admin import NestedModelAdmin, NestedStackedInline

from ...models.landyshevaya.main_page_models import (
    HeroPromotionSlideDescriptionCard,
    HeroPromotionSlideModel,
    LandyshevayaMainPageModel,
    CuratorsSectionModel,
    CtaSectionModel,
    TitleDescriptionSlideGalleryModel,
    TitleDescriptionSlideModel,
    TitleDescriptionSlidersSectionModel,
    OurWorkSectionModel,
    OurWorkImageGalleryModel,
    FaqFactoidsModel,
    FaqSectionModel,
)
from ..initial_admin import NestedSingletonModelAdmin


class FaqFactoidsAdmin(NestedStackedInline):
    model = FaqFactoidsModel
    extra = 1


class FaqSectionAdmin(NestedStackedInline):
    model = FaqSectionModel
    extra = 1
    max = 1
    inlines = [FaqFactoidsAdmin]


class OurWorkSectionGalleyAdmin(NestedStackedInline):
    model = OurWorkImageGalleryModel
    extra = 1


class OurWorkSectionAdmin(NestedStackedInline):
    model = OurWorkSectionModel
    extra = 1
    max = 1
    inlines = [OurWorkSectionGalleyAdmin]


class TitleDescriptionSlideGalleryAdmin(NestedStackedInline):
    model = TitleDescriptionSlideGalleryModel
    extra = 1


class TitleDescriptionSlideAdmin(NestedStackedInline):
    model = TitleDescriptionSlideModel
    extra = 1
    inlines = [TitleDescriptionSlideGalleryAdmin]


class TitleDescriptionSlidersSectionAdmin(NestedStackedInline):
    model = TitleDescriptionSlidersSectionModel
    extra = 1
    max_num = 1
    inlines = [TitleDescriptionSlideAdmin]


class CtaSectionInline(NestedStackedInline):
    model = CtaSectionModel
    extra = 1
    max_num = 1


class CuratorsSectionInline(NestedStackedInline):
    model = CuratorsSectionModel
    extra = 1
    max_num = 1


class HeroPromotionSlideDescriptionCardInline(NestedStackedInline):
    model = HeroPromotionSlideDescriptionCard
    extra = 1
    max_num = 1
    verbose_name = "Карточка слайда"
    verbose_name_plural = "Карточка слайда"
    fields = [
        "title",
        "content",
        "button_title",
        "button_href",
        "button_target",
        "is_open_feedback_modal",
    ]


class HeroPromotionSlideInline(NestedStackedInline):
    model = HeroPromotionSlideModel
    extra = 0
    sortable_field_name = "position"
    verbose_name = "Слайд акции"
    verbose_name_plural = "Слайдер Акций"
    fields = [
        "position",
        "title",
        "subtitle",
        "legend",
        "text_theme",
        "poster",
        "poster_mobile",
        "is_active",
    ]
    inlines = [HeroPromotionSlideDescriptionCardInline]


@admin.register(LandyshevayaMainPageModel)
class LandyshevayaMainPageAdmin(NestedModelAdmin, NestedSingletonModelAdmin):
    inlines = [
        HeroPromotionSlideInline,
        CuratorsSectionInline,
        CtaSectionInline,
        TitleDescriptionSlidersSectionAdmin,
        OurWorkSectionAdmin,
        FaqSectionAdmin
    ]

    def get_fieldsets(self, request, obj=None):
        # У самой страницы нет редактируемых полей — не показываем пустой
        # таб «Основная информация», оставляем только инлайны.
        return []
