import json
from django.test import TestCase, Client
from apps.branches.models import Branch
from apps.appointments.models import Appointment


class AppointmentModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )

    def test_create_appointment(self):
        appt = Appointment.objects.create(
            patient_name='Иван Иванов',
            patient_phone='+7-999-111-2233',
            branch=self.branch,
        )
        self.assertEqual(appt.status, Appointment.Status.NEW)
        self.assertEqual(str(appt), 'Иван Иванов — Центральный')

    def test_default_status_is_new(self):
        appt = Appointment.objects.create(
            patient_name='Мария',
            patient_phone='+7-999-111-0000',
            branch=self.branch,
        )
        self.assertEqual(appt.status, Appointment.Status.NEW)


class AppointmentAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )

    def test_create_appointment_via_api(self):
        payload = {
            'patient_name': 'Тест Тестов',
            'patient_phone': '+7-999-555-1234',
            'branch_id': self.branch.id,
            'comment': 'Болит зуб',
        }
        response = self.client.post(
            '/api/v1/appointments/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.count(), 1)
        appt = Appointment.objects.first()
        self.assertEqual(appt.patient_name, 'Тест Тестов')
        self.assertEqual(appt.status, Appointment.Status.NEW)

    def test_create_appointment_missing_required_field(self):
        payload = {'patient_name': 'Без телефона', 'branch_id': self.branch.id}
        response = self.client.post(
            '/api/v1/appointments/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 422)
