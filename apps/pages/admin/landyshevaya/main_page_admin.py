from urllib.parse import parse_qsl

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline

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
from ..initial_admin import SingletonModelAdmin


class FaqFactoidsInline(StackedInline):
    model = FaqFactoidsModel
    extra = 1


class FaqSectionInline(StackedInline):
    model = FaqSectionModel
    extra = 1
    max_num = 1
    inlines = [FaqFactoidsInline]


class OurWorkSectionGalleyInline(StackedInline):
    model = OurWorkImageGalleryModel
    extra = 1


class OurWorkSectionInline(StackedInline):
    model = OurWorkSectionModel
    extra = 1
    max_num = 1
    inlines = [OurWorkSectionGalleyInline]


class TitleDescriptionSlideInline(StackedInline):
    """Слайд «Наших преимуществ».

    Галерея слайда — третий уровень вложенности, который Unfold не умеет
    вкладывать в инлайн. Поэтому она вынесена в отдельный раздел админки
    и открывается ссылкой в новой вкладке.
    """

    model = TitleDescriptionSlideModel
    extra = 1
    readonly_fields = ["gallery_link"]

    @admin.display(description="Галерея слайда")
    def gallery_link(self, obj):
        if obj is None or obj.pk is None:
            return "Сохраните слайд — после этого появится ссылка на галерею."

        changelist_url = reverse(
            "admin:pages_titledescriptionslidegallerymodel_changelist"
        )
        add_url = reverse("admin:pages_titledescriptionslidegallerymodel_add")
        return format_html(
            '<a href="{}?slider__id__exact={}" target="_blank" rel="noopener">'
            "Открыть галерею</a> &nbsp;·&nbsp; "
            '<a href="{}?slider={}" target="_blank" rel="noopener">'
            "Добавить изображение</a>",
            changelist_url,
            obj.pk,
            add_url,
            obj.pk,
        )


class TitleDescriptionSlidersSectionInline(StackedInline):
    model = TitleDescriptionSlidersSectionModel
    extra = 1
    max_num = 1
    inlines = [TitleDescriptionSlideInline]


class CtaSectionInline(StackedInline):
    model = CtaSectionModel
    extra = 1
    max_num = 1


class CuratorsSectionInline(StackedInline):
    model = CuratorsSectionModel
    extra = 1
    max_num = 1


class HeroPromotionSlideDescriptionCardInline(StackedInline):
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


class HeroPromotionSlideInline(StackedInline):
    model = HeroPromotionSlideModel
    extra = 0
    ordering_field = "position"
    hide_ordering_field = True
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


@admin.register(TitleDescriptionSlideGalleryModel)
class TitleDescriptionSlideGalleryAdmin(ModelAdmin):
    """Галерея слайдов «Наших преимуществ».

    Живёт отдельно от главной страницы: слайд ссылается сюда, чтобы третий
    уровень вложенности не пришлось вкладывать в инлайн (Unfold так не умеет).
    """

    list_display = ("id", "slider", "preview")
    list_filter = ("slider",)
    list_select_related = ("slider",)

    @admin.display(description="Превью")
    def preview(self, obj):
        if obj.poster:
            return format_html(
                '<img src="{}" style="max-height: 80px; border-radius: 6px;">',
                obj.poster.url,
            )
        return "—"

    def get_changeform_initial_data(self, request):
        """Подставляет слайд при переходе «Добавить изображение».

        Ссылка из инлайна передаёт ``?slider=<id>``, а кнопка «Добавить»
        в отфильтрованном списке — ``_changelist_filters``.
        """
        initial = super().get_changeform_initial_data(request)

        slider_id = request.GET.get("slider")
        if not slider_id:
            preserved_filters = dict(
                parse_qsl(request.GET.get("_changelist_filters", ""))
            )
            slider_id = preserved_filters.get("slider__id__exact")

        if slider_id:
            initial["slider"] = slider_id

        return initial


@admin.register(LandyshevayaMainPageModel)
class LandyshevayaMainPageAdmin(SingletonModelAdmin):
    inlines = [
        HeroPromotionSlideInline,
        CuratorsSectionInline,
        CtaSectionInline,
        TitleDescriptionSlidersSectionInline,
        OurWorkSectionInline,
        FaqSectionInline,
    ]

    def get_fieldsets(self, request, obj=None):
        # У самой страницы нет редактируемых полей — не показываем пустой
        # таб «Основная информация», оставляем только инлайны.
        return []
