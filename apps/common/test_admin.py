from django.contrib import admin
from django.test import TestCase

from apps.pages.models.landyshevaya.main_page_models import (
    LandyshevayaMainPageModel,
    TitleDescriptionSlideModel,
    TitleDescriptionSlidersSectionModel,
)
from apps.users.models import User


class AdminSmokeTest(TestCase):
    """Все зарегистрированные модели должны открываться в админке (тема — Unfold).

    Ловит ошибки шаблонов и несовместимость сторонних админ-расширений
    (Unfold, вложенные инлайны, ckeditor) без ручного обхода разделов.
    """

    @classmethod
    def setUpTestData(cls):
        User.objects.create_superuser("admin", "admin@example.com", "pass")

    def setUp(self):
        self.client.force_login(User.objects.get(username="admin"))

    def test_model_admin_pages_render(self):
        urls = ["/admin/"]
        for model in admin.site._registry:
            opts = model._meta
            urls.append(f"/admin/{opts.app_label}/{opts.model_name}/")
            urls.append(f"/admin/{opts.app_label}/{opts.model_name}/add/")

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, url)

    def test_login_page_renders(self):
        self.client.logout()
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_main_page_change_form_renders_nested_inlines(self):
        """Unfold-инлайны второго уровня и ссылка на галерею третьего уровня."""
        page = LandyshevayaMainPageModel.objects.create()
        section = TitleDescriptionSlidersSectionModel.objects.create(page=page)
        slide = TitleDescriptionSlideModel.objects.create(section=section)

        response = self.client.get(
            f"/admin/pages/landyshevayamainpagemodel/{page.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Открыть галерею")
        self.assertContains(response, "slider__id__exact=")

        response = self.client.get(
            f"/admin/pages/titledescriptionslidegallerymodel/add/?slider={slide.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["adminform"].form.initial["slider"], str(slide.pk)
        )

    def test_main_page_saves_slide_nested_in_section(self):
        """Второй уровень вложенности (секция → слайд) сохраняется Unfold'ом."""
        page = LandyshevayaMainPageModel.objects.create()
        response = self.client.get(
            f"/admin/pages/landyshevayamainpagemodel/{page.pk}/change/"
        )
        formsets = {
            inline.formset.model: inline
            for inline in response.context["inline_admin_formsets"]
        }
        section_inline = formsets[TitleDescriptionSlidersSectionModel]
        section_prefix = section_inline.formset.prefix
        nested_inline = next(
            fs
            for fs in section_inline.formset.empty_form.nested_formsets
            if fs.formset.model is TitleDescriptionSlideModel
        )
        slide_prefix = nested_inline.formset.prefix.replace("__prefix__", "0")

        data = {}
        for inline in response.context["inline_admin_formsets"]:
            prefix = inline.formset.prefix
            data[f"{prefix}-TOTAL_FORMS"] = 0
            data[f"{prefix}-INITIAL_FORMS"] = 0
            data[f"{prefix}-MIN_NUM_FORMS"] = 0
            data[f"{prefix}-MAX_NUM_FORMS"] = 1

        data.update(
            {
                f"{section_prefix}-TOTAL_FORMS": 1,
                f"{section_prefix}-0-title": "Секция",
                f"{slide_prefix}-TOTAL_FORMS": 1,
                f"{slide_prefix}-INITIAL_FORMS": 0,
                f"{slide_prefix}-MIN_NUM_FORMS": 0,
                f"{slide_prefix}-MAX_NUM_FORMS": 1,
                f"{slide_prefix}-0-title": "Слайд",
                f"{slide_prefix}-0-description": "<p>Описание</p>",
            }
        )

        response = self.client.post(
            f"/admin/pages/landyshevayamainpagemodel/{page.pk}/change/", data
        )

        self.assertEqual(response.status_code, 302)
        section = TitleDescriptionSlidersSectionModel.objects.get(page=page)
        slide = TitleDescriptionSlideModel.objects.get(section=section)
        self.assertEqual(slide.title, "Слайд")


