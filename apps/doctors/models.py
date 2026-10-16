from django.db import models
from apps.common.mixins import ImageVariantsMixin
from django_ckeditor_5.fields import CKEditor5Field


class Doctor(ImageVariantsMixin, models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    patronymic = models.CharField(max_length=100, verbose_name="Отчество")
    photo = models.ImageField(
        upload_to="doctors/", blank=True, null=True, verbose_name="Фото"
    )
    photo_mobile = models.ImageField(
        upload_to="doctors/",
        blank=True,
        null=True,
        verbose_name="Фото (мобильная версия)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    job_referral = models.ManyToManyField(
        "DoctorReferral",
        blank=True,
        null=True,
        related_name="doctor_referral",
        verbose_name="Профессиональное направление",
    )

    IMAGE_VARIANT_FIELDS = ["photo", "photo_mobile"]

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"


class DoctorAccreditation(models.Model):
    """Документ врача: сама запись — группа, изображения лежат в DoctorAccreditationFile."""

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="accreditation",
        verbose_name="Врач",
    )
    title = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Название аккредитации"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Врачебная аккредитация"
        verbose_name_plural = "Врачебные аккредитации"
        ordering = ["-created_at"]

    def __str__(self):
        if self.title:
            return self.title
        if self.created_at:
            return f"Аккредитация от {self.created_at:%d.%m.%Y}"
        return "Аккредитация"


class DoctorAccreditationFile(ImageVariantsMixin, models.Model):
    accreditation = models.ForeignKey(
        DoctorAccreditation,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Аккредитация",
    )
    image = models.ImageField(
        upload_to="doctors/accreditation/", verbose_name="Изображение"
    )
    alt = models.CharField(max_length=255, blank=True, verbose_name="Alt-текст")
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок отображения"
    )

    IMAGE_VARIANT_FIELDS = ["image"]

    class Meta:
        verbose_name = "Файл аккредитации"
        verbose_name_plural = "Файлы аккредитации"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.alt or self.image.name or "Файл аккредитации"


class DoctorReferral(models.Model):
    title = models.CharField(
        max_length=255, verbose_name="Название направления", blank=True, null=True
    )
    description = CKEditor5Field(
        config_name="default",
        blank=True,
        verbose_name="Описание направления",
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Профессиональное направление"
        verbose_name_plural = "Профессиональные направления"

    def __str__(self):
        return self.title or "Направление без названия"


class DoctorBioInformation(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="bio",
        verbose_name="Врач",
    )
    title = models.CharField(
        max_length=255, verbose_name="Заголовок описания врача", blank=True, null=True
    )
    description = CKEditor5Field(
        config_name="default", blank=True, verbose_name="Описание врача", null=True
    )

    class Meta:
        verbose_name = "Информация о сотруднике"
        verbose_name_plural = "Информация о сотруднике"

    def __str__(self):
        return self.title or "Описание без заголовка"


class DoctorJobResults(ImageVariantsMixin, models.Model):
    author = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, verbose_name="Автор работ"
    )
    title = models.CharField(
        max_length=255, verbose_name="Заголовок описания работы", blank=True, null=True
    )
    description = CKEditor5Field(
        config_name="default", blank=True, verbose_name="Описание работы", null=True
    )
    photo_before = models.ImageField(
        upload_to="doctors/before", blank=True, null=True, verbose_name="Работа «до»"
    )
    photo_before_mobile = models.ImageField(
        upload_to="doctors/before",
        blank=True,
        null=True,
        verbose_name="Работа «до» (мобильная версия)",
    )
    photo_after = models.ImageField(
        upload_to="doctors/after", blank=True, null=True, verbose_name="Работа «после»"
    )
    photo_after_mobile = models.ImageField(
        upload_to="doctors/after",
        blank=True,
        null=True,
        verbose_name="Работа «после» (мобильная версия)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    IMAGE_VARIANT_FIELDS = [
        "photo_before",
        "photo_before_mobile",
        "photo_after",
        "photo_after_mobile",
    ]

    class Meta:
        verbose_name = "Результат работа сотрудника"
        verbose_name_plural = "Результат работ сотрудника"

    def __str__(self):
        return self.title or "Работа без заголовка"
