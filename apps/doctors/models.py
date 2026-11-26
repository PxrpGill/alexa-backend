from django.db import models
from uuid import uuid4
from apps.common.mixins import ImageVariantsMixin
from django.core.validators import MinValueValidator


class AboutDoctorTabContent(models.Model):
    title = models.TextField(verbose_name="Заголовок пункта")
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
        "AboutDoctorTab", on_delete=models.CASCADE, related_name="tab_contents"
    )

    class Meta:
        verbose_name = "Пункт раздела о сотруднике"
        verbose_name_plural = "Пункты разделов о сотруднике"

    def __str__(self):
        return self.title


class AboutDoctorTab(models.Model):
    slug = models.SlugField(verbose_name="Текстовый идентификатор")
    title = models.CharField(
        max_length=255,
        verbose_name="Название категории 'О сотруднике'",
        help_text="Значение может быть к примеру 'Образование', 'Повышение квалификации'",
    )

    doctor_information = models.ForeignKey(
        "AboutDoctorInformation", on_delete=models.CASCADE, related_name="doctor_tabs"
    )

    class Meta:
        verbose_name = "Раздел о сотруднике"
        verbose_name_plural = "Разделы о сотрудниках"

    def __str__(self):
        return self.title


class AboutDoctorInformation(models.Model):
    doctor = models.ForeignKey(
        "Doctor",
        on_delete=models.CASCADE,
        verbose_name="Привязка к сотруднику",
        related_name="doctor_informations",
    )

    class Meta:
        verbose_name = "Подробнее о сотруднике"
        verbose_name_plural = "Подробнее о сотрудниках"

    def __str__(self):
        return f"Информация о {self.doctor}"


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
        verbose_name = "Врач"
        verbose_name_plural = "Врачи"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name}"
