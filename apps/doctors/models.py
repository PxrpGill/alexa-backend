from django.db import models
from django.utils.text import slugify
from pytils.translit import slugify as t_slugify
from uuid import uuid4

from apps.common.mixins import ImageVariantsMixin
from apps.common.slugs import SLUG_BASE_MAX_LENGTH
from django.core.validators import MinValueValidator


class DoctorAccreditation(ImageVariantsMixin, models.Model):
    photo = models.ImageField(
        upload_to="doctors/", blank=True, null=True, verbose_name="Фото"
    )
    photo_mobile = models.ImageField(
        upload_to="doctors/",
        blank=True,
        null=True,
        verbose_name="Фото (мобильная версия)",
    )

    doctor = models.ForeignKey(
        "Doctor",
        on_delete=models.CASCADE,
        verbose_name="Привязка к сотруднику",
        related_name="doctor_accreditation",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Изображение аккредитации'
        verbose_name = 'Изображения аккредитации'

    def __str__(self):
        return "Изображение аккредитации"


class AboutDoctorTabContent(models.Model):
    title = models.TextField(verbose_name="Заголовок пункта", null=True, blank=True)
    description = models.TextField(
        verbose_name="Описание пункта", null=True, blank=True
    )
    year = models.IntegerField(
        verbose_name="Год прохождения",
        blank=True,
        null=True,
        validators=[MinValueValidator(1950)],
    )

    tab = models.ForeignKey(
        "AboutDoctorTab",
        on_delete=models.CASCADE,
        related_name="tab_contents",
        verbose_name="Категория",
        null=True,
        blank=True,
        help_text="Создаются в «Разделы о сотруднике»",
    )
    doctor = models.ForeignKey(
        "Doctor",
        on_delete=models.CASCADE,
        verbose_name="Привязка к сотруднику",
        related_name="doctor_detail_informations",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Пункт раздела о сотруднике"
        verbose_name_plural = "Пункты раздела о сотруднике"

    def __str__(self):
        return self.title


class AboutDoctorTab(models.Model):
    slug = models.SlugField(
        max_length=255,
        verbose_name="Текстовый идентификатор",
        null=True,
        blank=True,
        help_text="Создается автоматически",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Название категории «О сотруднике»",
        help_text="Значение может быть к примеру «Образовани», «Повышение квалификации»",
        null=True,
        blank=True,
    )

    doctor = models.ForeignKey(
        "Doctor",
        on_delete=models.CASCADE,
        verbose_name="Привязка к сотруднику",
        related_name="doctor_informations",
    )

    class Meta:
        verbose_name = "Раздел о сотруднике"
        verbose_name_plural = "Разделы о сотруднике"

    def __str__(self):
        return self.title or ""

    def save(self, *args, **kwargs):
        # Слаг — это tabKey на фронтенде, он должен быть читаемым и уникальным
        # внутри врача (ключи словаря content). Пустой слаг админ не даёт
        # заполнить руками: поле readonly.
        if not self.slug and self.doctor_id:
            base = (
                slugify(t_slugify(self.title or ""))[:SLUG_BASE_MAX_LENGTH]
                or f"section-{uuid4().hex[:8]}"
            )
            slug = base
            counter = 1

            while (
                AboutDoctorTab.objects.filter(doctor_id=self.doctor_id, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base}-{counter}"
                counter += 1

            self.slug = slug

        return super().save(*args, **kwargs)


class Doctor(ImageVariantsMixin, models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        unique=True,
        editable=False,
        verbose_name="Публичный идентификатор",
    )
    full_name = models.CharField(max_length=255, verbose_name="ФИО Сотрудника")
    position = models.CharField(
        max_length=255, verbose_name="Должность сотрудника", blank=True, null=True
    )
    photo = models.ImageField(
        upload_to="doctors/", blank=True, null=True, verbose_name="Фото"
    )
    photo_mobile = models.ImageField(
        upload_to="doctors/",
        blank=True,
        null=True,
        verbose_name="Фото (мобильная версия)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен на сайте")

    IMAGE_VARIANT_FIELDS = ["photo", "photo_mobile"]

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name}"
