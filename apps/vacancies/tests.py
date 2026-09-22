import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from apps.branch.models import BranchModel
from apps.common.test_utils import make_test_image
from apps.vacancies.models import (
    Application,
    Vacancy,
    VacancyBadge,
    VacancyBenefit,
    VacancyBenefitImage,
    VacancyCategory,
    VacancyRequirement,
    VacancyResponsibility,
)


def make_resume(
    name="resume.pdf",
    content=b"%PDF-1.4 test resume",
    content_type="application/pdf",
):
    return SimpleUploadedFile(name, content, content_type=content_type)


class VacanciesBaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(
            name="Аксайский район, ул. Ландышевая 104", slug="landyshevaya"
        )
        self.category = VacancyCategory.objects.create(name="Взрослая стоматология")
        self.vacancy = Vacancy.objects.create(
            category=self.category,
            name="Ассистент стоматолога",
            description="Помогайте врачам. Развивайтесь вместе с командой.",
            branch=self.branch,
            is_published=True,
            sort_order=1,
        )


class VacancyCategoryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(
            name="Аксайский район, ул. Ландышевая 104", slug="landyshevaya"
        )

    def test_category_auto_slug_transliterated(self):
        category = VacancyCategory.objects.create(name="Детская стоматология")
        self.assertEqual(category.slug, "detskaya-stomatologiya")

    def test_category_slug_unique_with_counter(self):
        VacancyCategory.objects.create(name="Детская стоматология")
        second = VacancyCategory.objects.create(name="Детская стоматология")
        self.assertEqual(second.slug, "detskaya-stomatologiya-1")


class VacancyListAPITest(VacanciesBaseTestCase):
    def test_list_returns_only_published(self):
        Vacancy.objects.create(
            category=self.category,
            name="Черновик",
            description="Скрытая",
            branch=self.branch,
            is_published=False,
        )
        response = self.client.get("/api/v1/vacancies")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["vacancy_name"], "Ассистент стоматолога")

    def test_list_item_is_lightweight_dto(self):
        response = self.client.get("/api/v1/vacancies")
        item = response.json()["results"][0]
        self.assertEqual(
            set(item.keys()), {"slug", "vacancy_name", "description", "branch"}
        )
        self.assertEqual(item["slug"], "assistent-stomatologa")
        self.assertEqual(item["branch"], "landyshevaya")

    def test_list_sorted_by_sort_order(self):
        Vacancy.objects.create(
            category=self.category,
            name="Первая",
            description="d",
            branch=self.branch,
            is_published=True,
            sort_order=0,
        )
        response = self.client.get("/api/v1/vacancies")
        names = [item["vacancy_name"] for item in response.json()["results"]]
        self.assertEqual(names, ["Первая", "Ассистент стоматолога"])

    def test_filter_by_category(self):
        other = VacancyCategory.objects.create(name="Администрация")
        Vacancy.objects.create(
            category=other,
            name="Администратор",
            description="d",
            branch=self.branch,
            is_published=True,
        )
        response = self.client.get(f"/api/v1/vacancies?category={other.slug}")
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["vacancy_name"], "Администратор")

    def test_categories_returned_in_envelope(self):
        inactive = VacancyCategory.objects.create(name="Отключённая", is_active=False)
        response = self.client.get("/api/v1/vacancies")
        categories = response.json()["categories"]
        slugs = [cat["slug"] for cat in categories]
        self.assertIn(self.category.slug, slugs)
        self.assertNotIn(inactive.slug, slugs)
        self.assertEqual(set(categories[0].keys()), {"slug", "name"})

    def test_total_counts_all_open_vacancies(self):
        other = VacancyCategory.objects.create(name="Администрация")
        Vacancy.objects.create(
            category=other,
            name="Администратор",
            description="d",
            branch=self.branch,
            is_published=True,
        )
        Vacancy.objects.create(
            category=self.category,
            name="Черновик",
            description="d",
            branch=self.branch,
            is_published=False,
        )
        response = self.client.get("/api/v1/vacancies")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)

    def test_without_category_uses_first_category_with_vacancies(self):
        VacancyCategory.objects.create(name="Пустая", sort_order=0)
        other = VacancyCategory.objects.create(name="Администрация", sort_order=1)
        Vacancy.objects.create(
            category=other,
            name="Администратор",
            description="d",
            branch=self.branch,
            is_published=True,
        )
        self.category.sort_order = 10
        self.category.save(update_fields=["sort_order"])
        response = self.client.get("/api/v1/vacancies")
        names = [item["vacancy_name"] for item in response.json()["results"]]
        self.assertEqual(names, ["Администратор"])

    def test_categories_without_vacancies_hidden(self):
        empty = VacancyCategory.objects.create(name="Пустая")
        response = self.client.get("/api/v1/vacancies")
        slugs = [cat["slug"] for cat in response.json()["categories"]]
        self.assertIn(self.category.slug, slugs)
        self.assertNotIn(empty.slug, slugs)

    def test_vacancy_from_inactive_category_not_shown(self):
        inactive = VacancyCategory.objects.create(name="Отключённая", is_active=False)
        Vacancy.objects.create(
            category=inactive,
            name="Скрытая",
            description="d",
            branch=self.branch,
            is_published=True,
        )
        response = self.client.get("/api/v1/vacancies")
        self.assertEqual(len(response.json()["results"]), 1)


class VacancyDetailAPITest(VacanciesBaseTestCase):
    def test_detail_by_slug(self):
        VacancyBadge.objects.create(vacancy=self.vacancy, text="Опыт от 1 года")
        response = self.client.get(f"/api/v1/vacancies/{self.vacancy.slug}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], self.vacancy.slug)
        self.assertEqual(data["hero"]["vacancy_name"], "Ассистент стоматолога")
        self.assertEqual(data["hero"]["badges"], ["Опыт от 1 года"])
        self.assertEqual(
            data["requirements"]["required"]["title"],
            "Наши обязательные требования",
        )
        self.assertEqual(
            data["requirements"]["partial"]["title"], "Будет вашим преимуществом"
        )
        self.assertEqual(data["responsibilities"]["title"], "Чем вы будете заниматься")

    def test_detail_contract_structure(self):
        VacancyRequirement.objects.create(
            vacancy=self.vacancy,
            type=VacancyRequirement.Type.REQUIRED,
            title="Опыт",
            description="Опыт от 1 года",
        )
        VacancyRequirement.objects.create(
            vacancy=self.vacancy,
            type=VacancyRequirement.Type.PARTIAL,
            title="Знание программ",
            description="Excel",
        )
        VacancyBenefit.objects.create(
            vacancy=self.vacancy, title="Профессиональный рост", description="Описание"
        )
        VacancyResponsibility.objects.create(
            vacancy=self.vacancy, title="Работа", description="Помощь врачу"
        )
        response = self.client.get(f"/api/v1/vacancies/{self.vacancy.slug}")
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"slug", "hero", "what_you_will_get", "requirements", "responsibilities"},
        )
        self.assertEqual(
            set(data["hero"].keys()), {"vacancy_name", "description", "badges"}
        )
        self.assertEqual(set(data["what_you_will_get"].keys()), {"images", "cards"})
        self.assertEqual(set(data["requirements"].keys()), {"required", "partial"})
        self.assertEqual(
            set(data["requirements"]["required"].keys()), {"title", "cards"}
        )
        card = data["requirements"]["required"]["cards"][0]
        self.assertEqual(set(card.keys()), {"icon", "title", "description"})
        self.assertEqual(set(data["responsibilities"].keys()), {"title", "cards"})
        self.assertEqual(
            set(data["responsibilities"]["cards"][0].keys()),
            {"image", "title", "description"},
        )
        self.assertEqual(
            set(data["what_you_will_get"]["cards"][0].keys()),
            {"title", "description"},
        )

    def test_unpublished_returns_404(self):
        draft = Vacancy.objects.create(
            category=self.category,
            name="Черновик",
            description="d",
            branch=self.branch,
            is_published=False,
        )
        response = self.client.get(f"/api/v1/vacancies/{draft.slug}")
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_returns_404(self):
        response = self.client.get("/api/v1/vacancies/no-such-vacancy")
        self.assertEqual(response.status_code, 404)


class VacancyImagesAPITest(VacanciesBaseTestCase):
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

    def test_benefit_images_returned_as_picture_format(self):
        VacancyBenefitImage.objects.create(
            vacancy=self.vacancy, image=make_test_image(name="benefit.jpg"), alt="Фото"
        )
        response = self.client.get(f"/api/v1/vacancies/{self.vacancy.slug}")
        self.assertEqual(response.status_code, 200)
        image = response.json()["what_you_will_get"]["images"][0]
        self.assertTrue(image["image"]["original"]["src"].endswith(".jpg"))
        self.assertEqual(image["alt"], "Фото")

    def test_responsibility_image_returned_as_picture_format(self):
        VacancyResponsibility.objects.create(
            vacancy=self.vacancy,
            image=make_test_image(name="resp.jpg"),
            title="Работа",
            description="Описание",
        )
        response = self.client.get(f"/api/v1/vacancies/{self.vacancy.slug}")
        data = response.json()
        image = data["responsibilities"]["cards"][0]["image"]
        self.assertTrue(image["original"]["src"].endswith(".jpg"))

    def test_requirement_icon_returned_as_plain_url(self):
        VacancyRequirement.objects.create(
            vacancy=self.vacancy,
            type=VacancyRequirement.Type.REQUIRED,
            icon=make_test_image(name="icon.png"),
            title="Иконка",
            description="d",
        )
        response = self.client.get(f"/api/v1/vacancies/{self.vacancy.slug}")
        data = response.json()
        icon = data["requirements"]["required"]["cards"][0]["icon"]
        self.assertTrue(icon.endswith("icon.png"))


class VacancyApplyAPITest(VacanciesBaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/api/v1/vacancies/{self.vacancy.slug}/apply"

    def test_successful_apply(self):
        response = self.client.post(
            self.url,
            {
                "name": "Иван Иванов",
                "phone": "+79991234567",
                "privacy_policy_accepted": "true",
                "resume": make_resume(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        application = Application.objects.get()
        self.assertEqual(application.vacancy, self.vacancy)
        self.assertEqual(application.name, "Иван Иванов")
        self.assertEqual(application.phone, "+79991234567")
        self.assertTrue(application.privacy_policy_accepted)
        self.assertIsNotNone(application.privacy_policy_accepted_at)
        self.assertEqual(application.status, Application.Status.NEW)
        self.assertTrue(application.resume.name.startswith("vacancies/resumes/"))
        self.assertTrue(application.resume.name.endswith(".pdf"))

    def test_apply_to_unpublished_returns_404(self):
        draft = Vacancy.objects.create(
            category=self.category,
            name="Черновик",
            description="d",
            branch=self.branch,
            is_published=False,
        )
        response = self.client.post(
            f"/api/v1/vacancies/{draft.slug}/apply",
            {
                "name": "Иван",
                "phone": "+79991234567",
                "privacy_policy_accepted": "true",
                "resume": make_resume(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 404)

    def test_apply_to_nonexistent_returns_404(self):
        response = self.client.post(
            "/api/v1/vacancies/no-such/apply",
            {
                "name": "Иван",
                "phone": "+79991234567",
                "privacy_policy_accepted": "true",
                "resume": make_resume(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 404)

    def _post(self, **overrides):
        defaults = {
            "name": "Иван Иванов",
            "phone": "+79991234567",
            "privacy_policy_accepted": "true",
        }
        data = {}
        for key, default in defaults.items():
            if key in overrides:
                if overrides[key] is not _MISSING:
                    data[key] = overrides[key]
            else:
                data[key] = default
        if "resume" in overrides:
            if overrides["resume"] is not _MISSING:
                data["resume"] = overrides["resume"]
        else:
            data["resume"] = make_resume()
        return self.client.post(self.url, data, format="multipart")

    def test_missing_name(self):
        response = self._post(name=_MISSING)
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())

    def test_empty_name(self):
        response = self._post(name="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())

    def test_whitespace_name(self):
        response = self._post(name="   ")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())

    def test_missing_phone(self):
        response = self._post(phone=_MISSING)
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())

    def test_invalid_phone(self):
        response = self._post(phone="не телефон")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())

    def test_missing_resume(self):
        response = self._post(resume=_MISSING)
        self.assertEqual(response.status_code, 400)
        self.assertIn("resume", response.json())

    def test_invalid_resume_extension(self):
        response = self._post(
            resume=SimpleUploadedFile(
                "virus.exe", b"MZ...", content_type="application/octet-stream"
            )
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("resume", response.json())

    def test_resume_content_does_not_match_extension(self):
        response = self._post(resume=make_resume(content=b"not a real pdf"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("resume", response.json())

    def test_oversized_resume(self):
        big = b"x" * (settings.MAX_RESUME_SIZE + 1)
        response = self._post(resume=make_resume(content=big))
        self.assertEqual(response.status_code, 400)
        self.assertIn("resume", response.json())

    def test_missing_privacy_policy_accepted(self):
        response = self._post(privacy_policy_accepted=_MISSING)
        self.assertEqual(response.status_code, 400)
        self.assertIn("privacy_policy_accepted", response.json())

    def test_privacy_policy_accepted_false(self):
        response = self._post(privacy_policy_accepted="false")
        self.assertEqual(response.status_code, 400)
        self.assertIn("privacy_policy_accepted", response.json())

    def test_no_application_created_on_validation_error(self):
        self._post(name=_MISSING)
        self.assertEqual(Application.objects.count(), 0)


_MISSING = object()


class GeneralApplyAPITest(VacanciesBaseTestCase):
    def test_general_apply_creates_application_without_vacancy(self):
        response = self.client.post(
            "/api/v1/vacancies/apply",
            {
                "name": "Иван Иванов",
                "phone": "+79991234567",
                "privacy_policy_accepted": "true",
                "resume": make_resume(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        application = Application.objects.get()
        self.assertIsNone(application.vacancy)
        self.assertTrue(application.privacy_policy_accepted)
