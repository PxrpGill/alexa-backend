from unittest.mock import patch
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from apps.promotions.models import Promotion, PromotionRequestFormModel


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
        self.assertNotIn("detail_content", data)
        self.assertIsNone(data["form"])

    def test_detail_contract_structure(self):
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"slug", "hero", "detail", "form"},
        )
        self.assertEqual(
            set(data["hero"].keys()),
            {
                "slug",
                "title",
                "description",
                "banner",
                "starts_at",
                "ends_at",
                "is_active",
            },
        )
        self.assertEqual(set(data["detail"].keys()), {"title", "content"})

    def test_hero_repeats_list_card_contract(self):
        list_card = self.client.get("/api/v1/promotions").json()[0]
        hero = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()[
            "hero"
        ]
        self.assertEqual(hero, list_card)

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

    def test_detail_returns_detail_content(self):
        self.promotion.detail_content = "<p>Программа лояльности и бонусы</p>"
        self.promotion.save()
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertEqual(
            data["detail_content"],
            "<p>Программа лояльности и&nbsp;бонусы</p>",
        )

    def test_empty_detail_sections_are_omitted(self):
        """Пустые секции (в т.ч. разметка CKEditor) не отдаются вовсе."""
        self.promotion.detail_title = ""
        self.promotion.detail_description = "<p>&nbsp;</p>"
        self.promotion.detail_content = "<p><br></p>"
        self.promotion.save()
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertNotIn("detail", data)
        self.assertNotIn("detail_content", data)

    def test_detail_section_drops_only_empty_field(self):
        self.promotion.detail_title = "  "
        self.promotion.save()
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertEqual(
            set(data["detail"].keys()),
            {"content"},
        )
        self.assertEqual(
            data["detail"]["content"],
            "<p>Консультация, снимок и&nbsp;установка импланта</p>",
        )

    def test_detail_returns_feedback_form(self):
        PromotionRequestFormModel.objects.create(
            promotion=self.promotion,
            title="Форма заявки на акцию",
            description="Заполните форму",
            button_text="Отправить",
        )
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertEqual(
            data["form"],
            {
                "title": "Форма заявки на&nbsp;акцию",
                "description": "Заполните форму",
                "button_text": "Отправить",
            },
        )


class PromotionOrderingTest(TestCase):
    """Порядок отдачи повторяет drag-n-drop в админке (поле order)."""

    def setUp(self):
        self.client = Client()
        self.today = timezone.localdate()

    def make(self, title, order, days_ago=0):
        promotion = Promotion.objects.create(
            title=title,
            starts_at=self.today - timedelta(days=days_ago),
            order=order,
        )
        return promotion

    def test_list_follows_order_field(self):
        # starts_at намеренно противоречит order: сортировать должно по order.
        third = self.make("Третья", order=2, days_ago=0)
        first = self.make("Первая", order=0, days_ago=5)
        second = self.make("Вторая", order=1, days_ago=2)

        slugs = [item["slug"] for item in self.client.get("/api/v1/promotions").json()]

        self.assertEqual(slugs, [first.slug, second.slug, third.slug])

    def test_new_promotion_goes_after_existing_at_equal_order(self):
        older = self.make("Старая", order=0, days_ago=10)
        newer = self.make("Новая", order=0, days_ago=0)

        slugs = [item["slug"] for item in self.client.get("/api/v1/promotions").json()]

        self.assertEqual(slugs, [newer.slug, older.slug])


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
            starts_at=timezone.localdate(),
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

    def test_api_keeps_service_fields_untouched(self):
        data = self.client.get(f"/api/v1/promotions/{self.promotion.slug}").json()
        self.assertEqual(data["slug"], self.promotion.slug)
        self.assertNotIn("&mdash;", data["slug"])

    def test_db_keeps_original_text(self):
        self.promotion.refresh_from_db()
        self.assertEqual(self.promotion.title, 'Акция "Белые зубы" - для всех')
        self.assertIn("style", self.promotion.description)
