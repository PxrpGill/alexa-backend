import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.common.test_utils import make_test_image

from .models import (
    Doctor,
    DoctorAccreditation,
    DoctorAccreditationFile,
    DoctorBioInformation,
    DoctorJobResults,
    DoctorReferral,
)


class DoctorStrTest(TestCase):
    """`__str__` обязан вернуть строку даже без заполненных полей.

    Иначе admin падает TypeError на `str(added_object)` при записи LogEntry.
    """

    def test_str_without_title_is_string(self):
        for model in (
            DoctorReferral,
            DoctorBioInformation,
            DoctorJobResults,
            DoctorAccreditation,
            DoctorAccreditationFile,
        ):
            with self.subTest(model=model.__name__):
                self.assertIsInstance(str(model()), str)

    def test_accreditation_str_with_date(self):
        doctor = Doctor.objects.create(
            first_name="Иван", last_name="Иванов", patronymic="Иванович"
        )
        accreditation = DoctorAccreditation.objects.create(doctor=doctor)
        self.assertIn("Аккредитация от", str(accreditation))

    def test_accreditation_str_prefers_title(self):
        doctor = Doctor.objects.create(
            first_name="Иван", last_name="Иванов", patronymic="Иванович"
        )
        accreditation = DoctorAccreditation.objects.create(
            doctor=doctor, title="Сертификат имплантолога"
        )
        self.assertEqual(str(accreditation), "Сертификат имплантолога")


class DoctorAdminAddTest(TestCase):
    """Создание врача с inline-блоком без заголовка не должно падать 500."""

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="pass12345"
        )
        self.client.force_login(self.admin)

    def test_add_doctor_with_untitled_inlines(self):
        data = {
            "first_name": "Иван",
            "last_name": "Иванов",
            "patronymic": "Иванович",
            "is_active": "on",
            # inline «Информация о сотруднике» — без заголовка, но с описанием
            "bio-TOTAL_FORMS": "1",
            "bio-INITIAL_FORMS": "0",
            "bio-MIN_NUM_FORMS": "0",
            "bio-MAX_NUM_FORMS": "1000",
            "bio-0-title": "",
            "bio-0-description": "<p>Описание</p>",
            # inline «Результат работ сотрудника» — тоже без заголовка
            "doctorjobresults_set-TOTAL_FORMS": "1",
            "doctorjobresults_set-INITIAL_FORMS": "0",
            "doctorjobresults_set-MIN_NUM_FORMS": "0",
            "doctorjobresults_set-MAX_NUM_FORMS": "1000",
            "doctorjobresults_set-0-title": "",
            "doctorjobresults_set-0-description": "<p>Работа</p>",
            # inline «Врачебная аккредитация»
            "accreditation-TOTAL_FORMS": "0",
            "accreditation-INITIAL_FORMS": "0",
            "accreditation-MIN_NUM_FORMS": "0",
            "accreditation-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(
            reverse("admin:doctors_doctor_add"), data, follow=True
        )

        self.assertEqual(response.status_code, 200)
        doctor = Doctor.objects.get(last_name="Иванов")
        self.assertEqual(doctor.bio.count(), 1)
        self.assertEqual(DoctorJobResults.objects.filter(author=doctor).count(), 1)


class MediaRootTestCase(TestCase):
    """Картинки тестов пишутся во временный MEDIA_ROOT, а не в проектный media/."""

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


class DoctorAccreditationFileTest(MediaRootTestCase):
    """К одной аккредитации прикрепляется несколько изображений."""

    def setUp(self):
        self.doctor = Doctor.objects.create(
            first_name="Иван", last_name="Иванов", patronymic="Иванович"
        )
        self.accreditation = DoctorAccreditation.objects.create(
            doctor=self.doctor, title="Сертификат имплантолога"
        )

    def test_several_files_attached_and_ordered(self):
        second = DoctorAccreditationFile.objects.create(
            accreditation=self.accreditation,
            image=make_test_image(name="page2.jpg"),
            sort_order=2,
        )
        first = DoctorAccreditationFile.objects.create(
            accreditation=self.accreditation,
            image=make_test_image(name="page1.jpg"),
            sort_order=1,
        )

        self.assertEqual(list(self.accreditation.files.all()), [first, second])

    def test_variants_generated_on_save(self):
        """ImageVariantsMixin подключён: рядом с оригиналом лежат webp/avif."""
        accreditation_file = DoctorAccreditationFile.objects.create(
            accreditation=self.accreditation, image=make_test_image(name="scan.jpg")
        )

        base, _ = os.path.splitext(accreditation_file.image.path)
        self.assertTrue(os.path.exists(f"{base}.webp"))
        self.assertTrue(os.path.exists(f"{base}.avif"))

    def test_str_falls_back_to_image_name(self):
        accreditation_file = DoctorAccreditationFile.objects.create(
            accreditation=self.accreditation, image=make_test_image(name="scan.jpg")
        )
        self.assertIn("scan", str(accreditation_file))


class DoctorAdminNestedAccreditationTest(MediaRootTestCase):
    """Файлы аккредитации редактируются вложенным inline в карточке врача."""

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="nested-admin", email="nested@example.com", password="pass12345"
        )
        self.client.force_login(self.admin)

    def _empty_inline(self, prefix, total=0):
        return {
            f"{prefix}-TOTAL_FORMS": str(total),
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

    def test_add_page_renders(self):
        response = self.client.get(reverse("admin:doctors_doctor_add"))
        self.assertEqual(response.status_code, 200)

    def test_add_doctor_with_two_accreditation_files(self):
        data = {
            "first_name": "Пётр",
            "last_name": "Петров",
            "patronymic": "Петрович",
            "is_active": "on",
            "accreditation-0-title": "Сертификат имплантолога",
            "accreditation-0-files-0-image": make_test_image(name="page1.jpg"),
            "accreditation-0-files-0-alt": "Страница 1",
            "accreditation-0-files-0-sort_order": "1",
            "accreditation-0-files-1-image": make_test_image(name="page2.jpg"),
            "accreditation-0-files-1-alt": "Страница 2",
            "accreditation-0-files-1-sort_order": "2",
        }
        data.update(self._empty_inline("bio"))
        data.update(self._empty_inline("doctorjobresults_set"))
        data.update(self._empty_inline("accreditation", total=1))
        data.update(self._empty_inline("accreditation-0-files", total=2))

        response = self.client.post(
            reverse("admin:doctors_doctor_add"), data, follow=True
        )

        self.assertEqual(response.status_code, 200)
        doctor = Doctor.objects.get(last_name="Петров")
        accreditation = doctor.accreditation.get()
        self.assertEqual(accreditation.title, "Сертификат имплантолога")
        self.assertEqual(
            [f.alt for f in accreditation.files.all()], ["Страница 1", "Страница 2"]
        )


class DoctorJobResultsVariantsTest(MediaRootTestCase):
    """Работы «до/после» тоже должны получать webp/avif."""

    def setUp(self):
        self.doctor = Doctor.objects.create(
            first_name="Иван", last_name="Иванов", patronymic="Иванович"
        )

    def test_variants_generated_for_all_photos(self):
        job_result = DoctorJobResults.objects.create(
            author=self.doctor,
            title="Имплантация",
            photo_before=make_test_image(name="before.jpg"),
            photo_before_mobile=make_test_image(name="before_m.jpg"),
            photo_after=make_test_image(name="after.jpg"),
            photo_after_mobile=make_test_image(name="after_m.jpg"),
        )

        for field_name in (
            "photo_before",
            "photo_before_mobile",
            "photo_after",
            "photo_after_mobile",
        ):
            with self.subTest(field=field_name):
                base, _ = os.path.splitext(getattr(job_result, field_name).path)
                self.assertTrue(os.path.exists(f"{base}.webp"))
                self.assertTrue(os.path.exists(f"{base}.avif"))


class DoctorAdminPreviewTest(MediaRootTestCase):
    """На странице врача рядом с полями картинок видны миниатюры."""

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="preview-admin", email="preview@example.com", password="pass12345"
        )
        self.client.force_login(self.admin)
        self.doctor = Doctor.objects.create(
            first_name="Иван",
            last_name="Иванов",
            patronymic="Иванович",
            photo=make_test_image(name="doctor.jpg"),
        )
        accreditation = DoctorAccreditation.objects.create(
            doctor=self.doctor, title="Сертификат"
        )
        DoctorAccreditationFile.objects.create(
            accreditation=accreditation, image=make_test_image(name="scan.jpg")
        )

    def test_change_page_shows_image_previews(self):
        response = self.client.get(
            reverse("admin:doctors_doctor_change", args=[self.doctor.pk])
        )
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        # фото врача + изображение файла аккредитации
        self.assertGreaterEqual(html.count('class="admin-image-preview"'), 2)
        self.assertIn("doctor", html)
        self.assertIn("scan", html)

    def test_changelist_shows_photo_preview(self):
        response = self.client.get(reverse("admin:doctors_doctor_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('class="admin-image-preview"', response.content.decode())
