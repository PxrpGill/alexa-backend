import uuid
from django.db import models
from django.utils.text import slugify
from pytils.translit import slugify as t_slugify

from apps.branch.models import BranchModel
from apps.common.mixins import ImageVariantsMixin


class VacancyCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(
        unique=True, verbose_name="Текстовый идентификатор категории", blank=True
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    class Meta:
        verbose_name = "Категория вакансии"
        verbose_name_plural = "Категории вакансий"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(t_slugify(self.name)) or f"category-{uuid.uuid4().hex[:8]}"
            slug = base
            counter = 1

            while (
                VacancyCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists()
            ):
                slug = f"{base}-{counter}"
                counter += 1

            self.slug = slug

        return super().save(*args, **kwargs)


def _unique_slug(instance, base):
    model_class = instance.__class__
    slug = base
    counter = 1

    while model_class.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{counter}"
        counter += 1

    return slug


class Vacancy(ImageVariantsMixin, models.Model):
    category = models.ForeignKey(
        VacancyCategory,
        on_delete=models.PROTECT,
        related_name="vacancies",
        verbose_name="Категория",
    )
    name = models.CharField(max_length=255, verbose_name="Название вакансии")
    slug = models.SlugField(
        unique=True, verbose_name="Текстовый идентификатор вакансии", blank=True
    )
    description = models.TextField(verbose_name="Краткое описание")
    branch = models.ForeignKey(
        BranchModel, on_delete=models.CASCADE, verbose_name="Филиал"
    )
    is_published = models.BooleanField(default=False, verbose_name="Опубликована")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )
    requirements_title = models.CharField(
        max_length=255,
        default="Наши обязательные требования",
        verbose_name="Заголовок обязательных требований",
    )
    partial_requirements_title = models.CharField(
        max_length=255,
        default="Будет вашим преимуществом",
        verbose_name="Заголовок преимуществ",
    )
    responsibilities_title = models.CharField(
        max_length=255,
        default="Чем вы будете заниматься",
        verbose_name="Заголовок обязанностей",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(t_slugify(self.name)) or f"vacancy-{uuid.uuid4().hex[:8]}"
            self.slug = _unique_slug(self, base)

        return super().save(*args, **kwargs)


class VacancyBadge(models.Model):
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="badges",
        verbose_name="Вакансия",
    )
    text = models.CharField(max_length=255, verbose_name="Текст")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    class Meta:
        verbose_name = "Бейдж вакансии"
        verbose_name_plural = "Бейджи вакансии"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.text


class VacancyBenefit(models.Model):
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="benefits",
        verbose_name="Вакансия",
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    class Meta:
        verbose_name = "Преимущество вакансии"
        verbose_name_plural = "Преимущества вакансии"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class VacancyBenefitImage(ImageVariantsMixin, models.Model):
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="benefit_images",
        verbose_name="Вакансия",
    )
    image = models.ImageField(
        upload_to="vacancies/benefits/", verbose_name="Изображение"
    )
    alt = models.CharField(max_length=255, blank=True, verbose_name="Alt-текст")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    IMAGE_VARIANT_FIELDS = ["image"]

    class Meta:
        verbose_name = "Изображение преимуществ"
        verbose_name_plural = "Изображения преимуществ"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.alt or self.image.name


class VacancyRequirement(models.Model):
    class Type(models.TextChoices):
        REQUIRED = "required", "Обязательное"
        PARTIAL = "partial", "Преимущество"

    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="requirements",
        verbose_name="Вакансия",
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.REQUIRED,
        verbose_name="Тип требования",
    )
    icon = models.ImageField(
        upload_to="vacancies/icons/", blank=True, verbose_name="Иконка"
    )
    title = models.CharField(max_length=255, blank=True, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    class Meta:
        verbose_name = "Требование вакансии"
        verbose_name_plural = "Требования вакансии"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title or self.description[:50]


class VacancyResponsibility(ImageVariantsMixin, models.Model):
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="responsibilities",
        verbose_name="Вакансия",
    )
    image = models.ImageField(
        upload_to="vacancies/responsibilities/", blank=True, verbose_name="Изображение"
    )
    title = models.CharField(max_length=255, blank=True, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    IMAGE_VARIANT_FIELDS = ["image"]

    class Meta:
        verbose_name = "Обязанность вакансии"
        verbose_name_plural = "Обязанности вакансии"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title or self.description[:50]


def resume_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"vacancies/resumes/{uuid.uuid4().hex}.{extension}"


class Application(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        PROCESSED = "processed", "Обработана"
        REJECTED = "rejected", "Отклонена"

    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
        verbose_name="Вакансия",
    )
    name = models.CharField(max_length=255, verbose_name="Имя")
    phone = models.CharField(max_length=30, verbose_name="Телефон")
    resume = models.FileField(
        upload_to=resume_upload_path, blank=True, verbose_name="Резюме"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Статус",
    )
    privacy_policy_accepted = models.BooleanField(
        default=False,
        verbose_name="Согласие на политику конфиденциальности",
    )
    privacy_policy_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата согласия на политику конфиденциальности",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Отклик"
        verbose_name_plural = "Отклики"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.vacancy or 'Общий отклик'}"
