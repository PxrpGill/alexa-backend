from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.branch.models import BranchModel


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class AppointmentMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(name="Центральный")

    def _payload(self, **overrides):
        payload = {
            "patient_name": "Иван Иванов",
            "patient_phone": "+79991234567",
            "branch_slug": self.branch.slug,
            "page_url": "/doctors",
            "is_ad_agreement": True,
            "is_privacy_agreement": True,
        }
        payload.update(overrides)
        return payload

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_appointment_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/appointments",
                self._payload(),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая запись на приём", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("+79991234567", text)
        self.assertIn("Центральный", text)
        self.assertIn("/admin/appointments/appointment/", text)

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_rejected_appointment_sends_nothing(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/appointments",
                self._payload(is_privacy_agreement=False),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        delay.assert_not_called()

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_appointment_without_branch_still_notifies(self, delay):
        from apps.appointments.models import Appointment

        with self.captureOnCommitCallbacks(execute=True):
            Appointment.objects.create(
                patient_name="Пётр Петров",
                patient_phone="+79990000000",
                branch=None,
                is_privacy_agreement=True,
            )

        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Пётр Петров", text)
        self.assertNotIn("Филиал", text)
        self.assertNotIn("None", text)
