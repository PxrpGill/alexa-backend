from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminSmokeTest(TestCase):
    """Каждая зарегистрированная модель открывается в админке.

    Ловит поломки от `fields` / `readonly_fields` / inline-наборов и от
    настроек jazzmin (`changeform_format_overrides`, кастомные CSS) сразу во
    всех приложениях: ошибка в наборе полей проявляется только при рендере.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="smoke-admin", email="smoke@example.com", password="pass12345"
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_changelist_and_add_pages_render(self):
        for model, _model_admin in admin.site._registry.items():
            label = f"{model._meta.app_label}.{model._meta.model_name}"
            with self.subTest(model=label):
                changelist = reverse(
                    f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
                )
                self.assertEqual(self.client.get(changelist).status_code, 200)

                add = reverse(
                    f"admin:{model._meta.app_label}_{model._meta.model_name}_add"
                )
                self.assertEqual(self.client.get(add).status_code, 200)
