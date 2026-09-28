from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch

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

    @patch("apps.common.tasks.send_max_notification_task.delay")
    @patch(
        "apps.common.max.admin_change_url",
        side_effect=NoReverseMatch("модель не зарегистрирована в админке"),
    )
    def test_broken_admin_link_does_not_break_the_lead(self, admin_url, delay):
        from apps.appointments.models import Appointment

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/appointments",
                self._payload(),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.count(), 1)
        delay.assert_not_called()


@override_settings(FRONTEND_URL="https://alexa.ru", MAX_NOTIFICATIONS_ENABLED=False)
class AppointmentPageUrlTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(name="Центральный")

    def test_page_url_points_to_the_site_not_the_api(self):
        from apps.appointments.models import Appointment

        response = self.client.post(
            "/api/v1/appointments",
            {
                "patient_name": "Иван Иванов",
                "patient_phone": "+79991234567",
                "branch_slug": self.branch.slug,
                "page_url": "/landyshevaya/terapiya-vz",
                "is_ad_agreement": True,
                "is_privacy_agreement": True,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get()
        self.assertEqual(
            appointment.page_url, "https://alexa.ru/landyshevaya/terapiya-vz"
        )
