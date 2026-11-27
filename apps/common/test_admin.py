from django.contrib import admin
from django.test import TestCase

from apps.users.models import User


class AdminSmokeTest(TestCase):
    """Все зарегистрированные модели должны открываться в админке (тема — Unfold).

    Ловит ошибки шаблонов и несовместимость сторонних админ-расширений
    (nested_admin, ckeditor) без ручного обхода разделов.
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
