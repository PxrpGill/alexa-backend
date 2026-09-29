from django.test import Client, TestCase

from apps.doctors.models import Doctor, Specialization


class DoctorTypographyTest(TestCase):
    """ФИО, специализации и HTML-биография врача типографируются при отдаче."""

    def setUp(self):
        self.client = Client()
        self.specialization = Specialization.objects.create(name='Терапевт - ортопед')
        self.doctor = Doctor.objects.create(
            first_name='Пётр',
            last_name='Иванов - Петров',
            patronymic='Петрович',
            bio='<p style="color:red">Врач в Москве - стаж 25 %</p>',
        )
        self.doctor.specializations.add(self.specialization)

    def test_api_typographs_plain_and_html_fields(self):
        data = self.client.get('/api/v1/doctors/').json()[0]
        self.assertEqual(data['last_name'], 'Иванов&nbsp;&mdash; Петров')
        self.assertEqual(data['specializations'][0]['name'], 'Терапевт&nbsp;&mdash; ортопед')
        self.assertNotIn('style', data['bio'])
        self.assertEqual(
            data['bio'],
            '<p>Врач в&nbsp;Москве&nbsp;&mdash; стаж 25&nbsp;%</p>',
        )

    def test_db_keeps_original_bio(self):
        self.doctor.refresh_from_db()
        self.assertIn('style', self.doctor.bio)
