import shutil
import tempfile

from django.contrib import admin as django_admin
from django.core.exceptions import ValidationError
from django import forms
from django.test import Client, RequestFactory, TestCase, override_settings

from apps.common.test_utils import make_test_image
from apps.branch.models import PagesModel
from apps.users.models import User
from apps.doctors.admin import AboutDoctorTabContentAdminForm
from apps.doctors.models import (
    AboutDoctorTab,
    AboutDoctorTabContent,
    Doctor,
    DoctorAccreditation,
)


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
        response = self.client.get(f'/api/v1/doctors/{self.doctor.pk}')
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

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}').json()

        keys = [tab['tabKey'] for tab in payload['aboutEmployee']['tabs']]
        self.assertNotIn('empty', keys)
        self.assertNotIn('empty', payload['aboutEmployee']['content'])

    def test_doctor_without_about_has_no_block(self):
        self.doctor.doctor_informations.all().delete()

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}').json()

        self.assertNotIn('aboutEmployee', payload)

    def test_inactive_doctor_is_hidden(self):
        self.doctor.is_active = False
        self.doctor.save()

        self.assertEqual(
            self.client.get(f'/api/v1/doctors/{self.doctor.pk}').status_code, 404
        )
        self.assertEqual(self.client.get('/api/v1/doctors').json(), [])

    def test_detail_returns_requested_doctor(self):
        other = Doctor.objects.create(full_name='Петров Пётр Петрович')

        payload = self.client.get(f'/api/v1/doctors/{other.pk}').json()

        self.assertEqual(payload['id'], str(other.pk))
        self.assertEqual(payload['fullname'], 'Петров Пётр Петрович')

    def test_list_shape(self):
        response = self.client.get('/api/v1/doctors')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['fullname'], self.doctor.full_name)
        self.assertEqual(
            payload[0]['aboutEmployee']['tabs'][0]['tabKey'], 'education',
        )


class DoctorPageFilterTest(TestCase):
    """?page_slug фильтрует список врачей по привязанной странице сайта."""

    def setUp(self):
        self.client = Client()
        self.home = PagesModel.objects.create(name='Главная')
        self.children = PagesModel.objects.create(name='Детская стоматология')
        self.on_home = Doctor.objects.create(full_name='Тарасова Ярослава Игоревна')
        self.on_children = Doctor.objects.create(full_name='Петров Пётр Петрович')
        self.on_both = Doctor.objects.create(full_name='Сидорова Анна Сергеевна')
        self.on_home.pages.add(self.home)
        self.on_children.pages.add(self.children)
        self.on_both.pages.add(self.home, self.children)

    def _names(self, query):
        response = self.client.get(f'/api/v1/doctors?{query}')
        self.assertEqual(response.status_code, 200)
        return [item['fullname'] for item in response.json()]

    def test_filters_by_page_slug(self):
        self.assertEqual(
            self._names(f'page_slug={self.children.slug}'),
            ['Петров Пётр Петрович', 'Сидорова Анна Сергеевна'],
        )

    def test_doctor_may_belong_to_several_pages(self):
        self.assertEqual(
            self._names(f'page_slug={self.home.slug}'),
            ['Сидорова Анна Сергеевна', 'Тарасова Ярослава Игоревна'],
        )

    def test_without_page_slug_returns_all(self):
        self.assertEqual(len(self._names('')), 3)

    def test_unknown_page_slug_gives_empty_list(self):
        self.assertEqual(self._names('page_slug=net-takoy-stranitsyi'), [])

    def test_inactive_doctor_is_hidden(self):
        self.on_children.is_active = False
        self.on_children.save()

        self.assertEqual(
            self._names(f'page_slug={self.children.slug}'),
            ['Сидорова Анна Сергеевна'],
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

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}').json()

        self.assertEqual(
            payload['aboutEmployee']['tabs'],
            [{'tabKey': tab.slug, 'tabTitle': 'Образование'}],
        )
        self.assertIn(tab.slug, payload['aboutEmployee']['content'])


class DoctorAccreditationTest(TestCase):
    """accreditation — массив картинок в формате PictureFormatSchema."""

    def setUp(self):
        self.client = Client()
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.doctor = Doctor.objects.create(full_name='Тарасова Ярослава Игоревна')

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_accreditation_is_picture_array(self):
        for name in ('accreditation-1.jpg', 'accreditation-2.jpg'):
            DoctorAccreditation.objects.create(
                doctor=self.doctor, photo=make_test_image(name=name),
            )

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}').json()

        pictures = payload['accreditation']
        self.assertEqual(len(pictures), 2)
        for picture in pictures:
            self.assertTrue(picture['original']['src'].startswith('/media/doctors/'))
            # вариантов нет — мобильная версия не подставляется, а не приходит null
            self.assertNotIn('mobile', picture['original'])

    def test_items_without_photo_are_skipped(self):
        DoctorAccreditation.objects.create(doctor=self.doctor)
        DoctorAccreditation.objects.create(
            doctor=self.doctor, photo=make_test_image(name='accreditation.jpg'),
        )

        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}').json()

        self.assertEqual(len(payload['accreditation']), 1)

    def test_no_accreditation_gives_empty_array(self):
        payload = self.client.get(f'/api/v1/doctors/{self.doctor.pk}').json()

        self.assertEqual(payload['accreditation'], [])


class AboutDoctorTabBelongsToDoctorTest(TestCase):
    """Раздел, созданный на враче, недоступен в пунктах другого врача."""

    def setUp(self):
        self.doctor = Doctor.objects.create(full_name='Тарасова Ярослава Игоревна')
        self.other = Doctor.objects.create(full_name='Петров Пётр Петрович')
        self.tab = AboutDoctorTab.objects.create(
            doctor=self.doctor, title='Образование',
        )
        self.other_tab = AboutDoctorTab.objects.create(
            doctor=self.other, title='Повышение квалификации',
        )

        user = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.request = RequestFactory().get('/')
        self.request.user = user
        self.inline = AboutDoctorTabContentAdminForm(Doctor, django_admin.site)

    def _tab_field(self, doctor):
        formset = self.inline.get_formset(self.request, obj=doctor)
        return formset.form.base_fields['tab']

    def test_inline_lists_only_tabs_of_the_doctor(self):
        queryset = self._tab_field(self.other).queryset

        self.assertEqual(list(queryset), [self.other_tab])

    def test_inline_has_no_tabs_for_unsaved_doctor(self):
        queryset = self._tab_field(None).queryset

        self.assertEqual(list(queryset), [])

    def test_parent_doctor_is_hidden_in_inline(self):
        # FK на врача в инлайне — скрытое поле InlineForeignKeyField,
        # подменить врача через форму нельзя.
        formset = self.inline.get_formset(self.request, obj=self.doctor)()

        self.assertIsInstance(
            formset.empty_form.fields['doctor'].widget, forms.HiddenInput,
        )

    def test_foreign_tab_is_rejected_by_validation(self):
        content = AboutDoctorTabContent(
            doctor=self.other, tab=self.tab, title='ЧГУ',
        )

        with self.assertRaises(ValidationError):
            content.full_clean()

    def test_save_keeps_doctor_in_sync_with_tab(self):
        content = AboutDoctorTabContent.objects.create(
            doctor=self.other, tab=self.tab, title='ЧГУ',
        )

        content.refresh_from_db()
        self.assertEqual(content.doctor_id, self.doctor.pk)

    def test_content_of_foreign_tab_is_not_served(self):
        # Даже если данные разошлись в обход формы (например, из shell),
        # API группирует пункты по разделу врача, а не по полю doctor.
        content = AboutDoctorTabContent.objects.create(
            doctor=self.doctor, tab=self.tab, title='ЧГУ',
        )
        AboutDoctorTabContent.objects.filter(pk=content.pk).update(
            doctor_id=self.other.pk,
        )

        payload = self.client.get(f'/api/v1/doctors/{self.other.pk}').json()

        self.assertNotIn('aboutEmployee', payload)
