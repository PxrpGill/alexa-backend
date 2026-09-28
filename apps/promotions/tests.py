from unittest.mock import patch
import shutil
import tempfile
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import resolve
from django.utils import timezone

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
from apps.promotions.models import Promotion, PromotionCondition


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
        self.assertEqual(data["hero"]["description"], "<p>Скидка 20% на имплантацию</p>")
        self.assertEqual(data["detail"]["title"], "Что входит в акцию")
        self.assertEqual(
            data["detail"]["content"],
            "<p>Консультация, снимок и установка импланта</p>",
        )

    def test_detail_contract_structure(self):
        PromotionCondition.objects.create(
            promotion=self.promotion,
            title="Срок",
            description="Акция действует до конца месяца",
        )
        response = self.client.get(f"/api/v1/promotions/{self.promotion.slug}")
        data = response.json()
        self.assertEqual(set(data.keys()), {"slug", "hero", "detail", "conditions"})
        self.assertEqual(set(data["detail"].keys()), {"title", "content"})
        self.assertEqual(set(data["conditions"].keys()), {"title", "cards"})
        card = data["conditions"]["cards"][0]
        self.assertEqual(set(card.keys()), {"icon", "title", "description"})

    def test_hero_repeats_list_card_contract(self):
        list_card = self.client.get("/api/v1/promotions").json()[0]
        hero = self.client.get(
            f"/api/v1/promotions/{self.promotion.slug}"
        ).json()["hero"]
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
