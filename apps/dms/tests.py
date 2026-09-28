from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.branch.models import BranchModel


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class DMSMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(name="Центральный")

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_dms_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/dms",
                {
                    "patient_name": "Иван Иванов",
                    "patient_phone": "+79991234567",
                    "branch_slug": self.branch.slug,
                    "page_url": "/dms",
                    "is_ad_agreement": True,
                    "is_privacy_agreement": True,
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая заявка ДМС", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("Центральный", text)
        self.assertIn("/admin/dms/dms/", text)
