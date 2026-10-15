from unittest.mock import patch
import shutil
import tempfile
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from django.contrib import admin
from django.contrib.auth import get_user_model

from apps.promotions.admin import (
    PromotionTargetAudience,
    PromotionWhatInclude,
    PromotionWhyItMatters,
)
from apps.promotions.models import Promotion


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class PromotionRequestMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.promotion = Promotion.objects.create(
            title="Чистка со скидкой",
            is_active=True,
            starts_at=timezone.localdate(),
        )

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_request_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/promotions/request",
                {
                    "patient_name": "Иван Иванов",
                    "patient_phone": "+79991234567",
                    "slug": self.promotion.slug,
                    "is_ad_agreement": True,
                    "is_privacy_agreement": True,
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая заявка на акцию", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("Чистка со скидкой", text)
        self.assertIn("/admin/promotions/promotionrequests/", text)


from apps.common.test_utils import make_test_image
from apps.promotions.models import (
    Promotion,
    PromotionCondition,
    TargetAudience,
    WhatPromotionInclude,
    WhyItMatters,
)


class PromotionAdminEmptyInlineTest(TestCase):
    """Пустая строка инлайна не должна сохраняться: CKEditor пишет в поле
    разметку вида "<p><br></p>", из-за чего Django считает форму изменённой
    и без фильтра создавал бы пустые записи."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-empty-inline", email="", password="x"
        )
        self.request = type("AdminRequest", (), {"user": self.user})()
        self.promotion = Promotion.objects.create(
            title="Без секций", starts_at=timezone.localdate()
        )

    def _save_inline(self, inline_cls, model, title, description):
        formset_class = inline_cls(Promotion, admin.site).get_formset(
            self.request, self.promotion
        )
        formset = formset_class(
            data={
                "f-TOTAL_FORMS": "1",
                "f-INITIAL_FORMS": "0",
                "f-MIN_NUM_FORMS": "0",
                "f-MAX_NUM_FORMS": formset_class.max_num,
                "f-0-title": title,
                "f-0-description": description,
            },
            files=None,
            instance=self.promotion,
            prefix="f",
        )
        self.assertTrue(formset.is_valid())
        formset.save()

    def test_empty_ckeditor_rows_are_not_created(self):
        for inline_cls, model in [
            (PromotionTargetAudience, TargetAudience),
            (PromotionWhatInclude, WhatPromotionInclude),
            (PromotionWhyItMatters, WhyItMatters),
        ]:
            with self.subTest(model=model.__name__):
                self._save_inline(inline_cls, model, "", "<p><br></p>")
                self.assertEqual(
                    model.objects.filter(promotion=self.promotion).count(), 0
                )

    def test_filled_row_is_created(self):
        self._save_inline(
            PromotionTargetAudience, TargetAudience, "Кому подходит", "<p>Взрослым</p>"
        )
        row = TargetAudience.objects.get(promotion=self.promotion)
        self.assertEqual(row.title, "Кому подходит")
        self.assertEqual(row.description, "<p>Взрослым</p>")


class PromotionsBaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = timezone.localdate()
        self.promotion = Promotion.objects.create(
            title="Имплантация под ключ",
            description="<p>Скидка 20% на имплантацию</p>",
            detail_title="Что входит в акцию",
            detail_description="<p>Консультация, снимок и установка импланта</p>",
            starts_at=self.today - timedelta(days=1),
        )


class PromotionDetailAPITest(PromotionsBaseTestCase):
    def test_detail_by_slug(self):
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], self.promotion.slug)
        self.assertEqual(data["hero"]["title"], "Имплантация под ключ")
        self.assertEqual(
            data["hero"]["description"],
            "<p>Скидка 20% на&nbsp;имплантацию</p>",
        )
        self.assertEqual(data["detail"]["title"], "Что входит в&nbsp;акцию")
        self.assertEqual(
            data["detail"]["content"],
            "<p>Консультация, снимок и&nbsp;установка импланта</p>",
        )

    def test_detail_contract_structure(self):
        PromotionCondition.objects.create(
            promotion=self.promotion,
            title="Срок",
            description="Акция действует до конца месяца",
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {
                "slug",
                "hero",
                "detail",
                "conditions",
                "target_audience",
                "what_promotion_include",
                "why_it_matters",
            },
        )
        self.assertEqual(set(data["detail"].keys()), {"title", "content"})
        self.assertEqual(set(data["conditions"].keys()), {"title", "cards"})
        card = data["conditions"]["cards"][0]
        self.assertEqual(set(card.keys()), {"icon", "title", "description"})

    def test_hero_repeats_list_card_contract(self):
        list_card = self.client.get("/api/v1/promotions").json()[0]
        hero = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()[
            "hero"
        ]
        self.assertEqual(hero, list_card)

    def test_conditions_default_title(self):
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.json()["conditions"]["title"], "Условия акции")

    def test_conditions_ordered_by_sort_order(self):
        PromotionCondition.objects.create(
            promotion=self.promotion, title="Второе", description="b", sort_order=2
        )
        PromotionCondition.objects.create(
            promotion=self.promotion, title="Первое", description="a", sort_order=1
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        titles = [card["title"] for card in response.json()["conditions"]["cards"]]
        self.assertEqual(titles, ["Первое", "Второе"])

    def test_detail_unknown_slug_returns_404(self):
        response = self.client.get("/api/v1/promotions/net-takoy-akcii")
        self.assertEqual(response.status_code, 404)

    def test_detail_inactive_promotion_returns_404(self):
        self.promotion.is_active = False
        self.promotion.save()
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.status_code, 404)

    def test_detail_expired_promotion_returns_404(self):
        self.promotion.ends_at = self.today - timedelta(days=1)
        self.promotion.save()
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.status_code, 404)

    def test_detail_future_promotion_returns_404(self):
        self.promotion.starts_at = self.today + timedelta(days=1)
        self.promotion.save()
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.status_code, 404)

    def test_detail_without_conditions_returns_empty_cards(self):
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.json()["conditions"]["cards"], [])

    def test_detail_returns_new_sections(self):
        TargetAudience.objects.create(
            promotion=self.promotion,
            title="Кому подходит",
            description="Взрослым и детям",
        )
        WhatPromotionInclude.objects.create(
            promotion=self.promotion,
            title="Что входит",
            description="Имплант и коронка",
        )
        WhyItMatters.objects.create(
            promotion=self.promotion,
            title="Почему важно",
            description="Гарантия 10 лет",
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        data = response.json()
        self.assertEqual(data["target_audience"][0]["title"], "Кому подходит")
        self.assertEqual(data["what_promotion_include"][0]["title"], "Что входит")
        self.assertEqual(data["why_it_matters"][0]["title"], "Почему важно")

    def test_detail_skips_empty_section_rows(self):
        TargetAudience.objects.create(
            promotion=self.promotion, title="", description="<p><br></p>"
        )
        WhatPromotionInclude.objects.create(
            promotion=self.promotion, title="", description="<p>&nbsp;</p>"
        )
        WhyItMatters.objects.create(promotion=self.promotion)
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        data = response.json()
        self.assertEqual(data["target_audience"], [])
        self.assertEqual(data["what_promotion_include"], [])
        self.assertEqual(data["why_it_matters"], [])

    def test_detail_keeps_only_non_empty_section_rows(self):
        TargetAudience.objects.create(
            promotion=self.promotion, title="", description="<p><br></p>"
        )
        TargetAudience.objects.create(
            promotion=self.promotion,
            title="Кому подходит",
            description="Взрослым",
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        rows = response.json()["target_audience"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Кому подходит")


class PromotionConditionImageTest(PromotionsBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def test_condition_icon_returned_as_source_url(self):
        """Иконка условия отдаётся ссылкой на исходный файл, без webp/avif."""
        PromotionCondition.objects.create(
            promotion=self.promotion,
            icon=make_test_image(name="condition.jpg"),
            title="Гарантия",
            description="Гарантия на имплант 10 лет",
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.status_code, 200)
        icon = response.json()["conditions"]["cards"][0]["icon"]
        self.assertIsInstance(icon, str)
        self.assertTrue(icon.endswith(".jpg"))

    def test_condition_icon_accepts_svg(self):
        PromotionCondition.objects.create(
            promotion=self.promotion,
            icon=SimpleUploadedFile(
                "condition.svg",
                b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
                content_type="image/svg+xml",
            ),
            title="Рассрочка",
            description="Рассрочка на 12 месяцев",
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        icon = response.json()["conditions"]["cards"][0]["icon"]
        self.assertTrue(icon.endswith(".svg"))

    def test_condition_icon_rejects_unsupported_extension(self):
        condition = PromotionCondition(
            promotion=self.promotion,
            icon=SimpleUploadedFile("condition.exe", b"MZ"),
            title="Плохая иконка",
            description="Описание",
        )
        with self.assertRaises(ValidationError):
            condition.full_clean()

    def test_condition_without_icon_returns_empty_string(self):
        PromotionCondition.objects.create(
            promotion=self.promotion, title="Без иконки", description="Описание"
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        self.assertEqual(response.json()["conditions"]["cards"][0]["icon"], "")


class PromotionRouteOrderTest(TestCase):
    """Шаблон "/{slug}" совпадает и с "/request", а Django резолвит пути
    в порядке регистрации: если detail-роут объявить выше lead-формы,
    POST /promotions/request вернёт 405 и заявки на акцию перестанут доходить."""

    def test_request_path_is_not_captured_by_slug_route(self):
        match = resolve("/api/v1/promotions/request")

        self.assertEqual(match.kwargs, {})

    def test_slug_path_still_resolves_to_detail(self):
        match = resolve("/api/v1/promotions/letnyaya-akciya")

        self.assertEqual(match.kwargs, {"slug": "letnyaya-akciya"})


class PromotionSlugLengthTest(TestCase):
    """Заголовок акции — до 500 символов, а slug генерируется из него
    транслитерацией, поэтому основа обрезается: иначе INSERT падает
    с DataError «value too long»."""

    def test_long_title_produces_slug_within_field_length(self):
        max_length = Promotion._meta.get_field("slug").max_length
        promotion = Promotion.objects.create(
            title="Щётка " * 80,
            starts_at=timezone.localdate(),
        )

        self.assertLessEqual(len(promotion.slug), max_length)

    def test_long_title_collision_gets_counter_suffix(self):
        title = "Щётка " * 80
        first = Promotion.objects.create(title=title, starts_at=timezone.localdate())
        second = Promotion.objects.create(title=title, starts_at=timezone.localdate())

        self.assertEqual(second.slug, f"{first.slug}-1")
        self.assertLessEqual(
            len(second.slug), Promotion._meta.get_field("slug").max_length
        )


class PromotionTypographyTest(TestCase):
    """Тексты акции типографируются при отдаче, в БД остаётся исходник."""

    def setUp(self):
        self.client = Client()
        self.promotion = Promotion.objects.create(
            title='Акция "Белые зубы" - для всех',
            description='<p style="color:red">Скидка 20 % на чистку</p>',
            detail_title="Что входит - список",
            detail_description="<p>Консультация и снимок</p>",
            conditions_title="Условия - важно",
            starts_at=timezone.localdate(),
        )
        PromotionCondition.objects.create(
            promotion=self.promotion,
            title="Срок - до конца месяца",
            description="Действует в Москве",
        )

    def test_api_typographs_plain_and_html_fields(self):
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertEqual(
            data["hero"]["title"], "Акция «Белые зубы»&nbsp;&mdash; для всех"
        )
        self.assertEqual(
            data["hero"]["description"], "<p>Скидка 20&nbsp;% на&nbsp;чистку</p>"
        )
        self.assertNotIn("style", data["hero"]["description"])
        self.assertEqual(data["detail"]["title"], "Что входит&nbsp;&mdash; список")
        self.assertEqual(data["conditions"]["title"], "Условия&nbsp;&mdash; важно")
        card = data["conditions"]["cards"][0]
        self.assertEqual(card["title"], "Срок&nbsp;&mdash; до&nbsp;конца месяца")
        self.assertEqual(card["description"], "Действует в&nbsp;Москве")

    def test_api_keeps_service_fields_untouched(self):
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertEqual(data["slug"], self.promotion.slug)
        self.assertNotIn("&mdash;", data["slug"])
        self.assertEqual(data["conditions"]["cards"][0]["icon"], "")

    def test_db_keeps_original_text(self):
        self.promotion.refresh_from_db()
        self.assertEqual(self.promotion.title, 'Акция "Белые зубы" - для всех')
        self.assertIn("style", self.promotion.description)
