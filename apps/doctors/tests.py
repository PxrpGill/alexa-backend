from django.test import Client, TestCase

from apps.doctors.models import AboutDoctorTab, AboutDoctorTabContent, Doctor


class DoctorApiTest(TestCase):
    """Форма ответа /api/v1/doctors совпадает с контрактом фронтенда."""

    def setUp(self):
        self.client = Client()
        self.doctor = Doctor.objects.create(
            full_name='Тарасова Ярослава Игоревна',
            position='Детский стоматолог',
        )
        education = AboutDoctorTab.objects.create(
            doctor=self.doctor, slug='education', title='Образование',
        )
        AboutDoctorTabContent.objects.create(
            doctor=self.doctor,
            tab=education,
            title='Чувашский государственный университет',
            description='Стоматология',
            year=2022,
        )
        development = AboutDoctorTab.objects.create(
            doctor=self.doctor,
            slug='professional-development',
            title='Повышение квалификации',
        )
        AboutDoctorTabContent.objects.create(
            doctor=self.doctor, tab=development, title='Эндодонтия', year=2025,
        )
        AboutDoctorTabContent.objects.create(
            doctor=self.doctor, tab=development, title='Травма молочных зубов', year=2024,
        )

    def test_detail_shape(self):
        response = self.client.get(f'/api/v1/doctors/{self.doctor.pk}/')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload['id'], str(self.doctor.pk))
        self.assertEqual(payload['fullname'], self.doctor.full_name)
        self.assertEqual(payload['position'], self.doctor.position)
        self.assertNotIn('poster', payload)  # нет фото — ключ не отдаётся

        about = payload['aboutEmployee']
        self.assertEqual(
            about['tabs'],
            [
                {'tabKey': 'education', 'tabTitle': 'Образование'},
                {
                    'tabKey': 'professional-development',
                    'tabTitle': 'Повышение квалификации',
                },
            ],
        )

        education = about['content']['education']
        self.assertEqual(education['title'], 'Образование')
        self.assertEqual(len(education['content']), 1)
        self.assertEqual(
            education['content'][0],
            {
                'title': 'Чувашский государственный университет',
                'description': 'Стоматология',
                'year': 2022,
            },
        )

        development = about['content']['professional-development']
        self.assertEqual(
            [item['title'] for item in development['content']],
            ['Эндодонтия', 'Травма молочных зубов'],
        )
        # отсутствующий description не отдаётся, а не приходит как null
        self.assertNotIn('description', development['content'][0])

    def test_empty_tabs_are_skipped(self):
        AboutDoctorTab.objects.create(
            doctor=self.doctor, slug='empty', title='Без пунктов',
        )

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}/').json()

        keys = [tab['tabKey'] for tab in payload['aboutEmployee']['tabs']]
        self.assertNotIn('empty', keys)
        self.assertNotIn('empty', payload['aboutEmployee']['content'])

    def test_doctor_without_about_has_no_block(self):
        self.doctor.doctor_informations.all().delete()

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}/').json()

        self.assertNotIn('aboutEmployee', payload)

    def test_inactive_doctor_is_hidden(self):
        self.doctor.is_active = False
        self.doctor.save()

        self.assertEqual(
            self.client.get(f'/api/v1/doctors/{self.doctor.pk}/').status_code, 404
        )
        self.assertEqual(self.client.get('/api/v1/doctors/').json(), [])

    def test_detail_returns_requested_doctor(self):
        other = Doctor.objects.create(full_name='Петров Пётр Петрович')

        payload = self.client.get(f'/api/v1/doctors/{other.pk}/').json()

        self.assertEqual(payload['id'], str(other.pk))
        self.assertEqual(payload['fullname'], 'Петров Пётр Петрович')

    def test_list_shape(self):
        response = self.client.get('/api/v1/doctors/')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['fullname'], self.doctor.full_name)
        self.assertEqual(
            payload[0]['aboutEmployee']['tabs'][0]['tabKey'], 'education',
        )


class AboutDoctorTabSlugTest(TestCase):
    """tabKey на фронтенде — это slug раздела, он генерируется из заголовка."""

    def setUp(self):
        self.client = Client()
        self.doctor = Doctor.objects.create(full_name='Тарасова Ярослава Игоревна')
        self.other = Doctor.objects.create(full_name='Петров Пётр Петрович')

    def test_slug_is_generated_from_title(self):
        tab = AboutDoctorTab.objects.create(
            doctor=self.doctor, title='Повышение квалификации',
        )

        self.assertEqual(tab.slug, 'povyishenie-kvalifikatsii')

    def test_slug_is_unique_within_doctor(self):
        AboutDoctorTab.objects.create(doctor=self.doctor, title='Образование')
        second = AboutDoctorTab.objects.create(
            doctor=self.doctor, title='Образование',
        )

        self.assertEqual(second.slug, 'obrazovanie-1')

    def test_slug_may_repeat_for_different_doctors(self):
        first = AboutDoctorTab.objects.create(
            doctor=self.doctor, title='Образование',
        )
        second = AboutDoctorTab.objects.create(
            doctor=self.other, title='Образование',
        )

        self.assertEqual(first.slug, second.slug)

    def test_empty_title_falls_back_to_generated_key(self):
        tab = AboutDoctorTab.objects.create(doctor=self.doctor, title=None)

        self.assertTrue(tab.slug.startswith('section-'))

    def test_generated_slug_becomes_tab_key(self):
        tab = AboutDoctorTab.objects.create(
            doctor=self.doctor, title='Образование',
        )
        AboutDoctorTabContent.objects.create(
            doctor=self.doctor, tab=tab, title='ЧГУ', year=2022,
        )

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}/').json()

        self.assertEqual(
            payload['aboutEmployee']['tabs'],
            [{'tabKey': tab.slug, 'tabTitle': 'Образование'}],
        )
        self.assertIn(tab.slug, payload['aboutEmployee']['content'])
