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
    job_referral = models.ManyToManyField("DoctorReferral", blank=True, related_name="doctor_referral", verbose_name="Профессиональное направление")

    IMAGE_VARIANT_FIELDS = ["photo", "photo_mobile"]

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"


class DoctorAccreditation(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="accreditation",
        verbose_name="Врач",
    )
    photo = models.ImageField(
        upload_to="doctors/accreditation",
        blank=True,
        null=True,
        verbose_name="Изображение аккредитации",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    IMAGE_VARIANT_FIELDS = ["photo", "photo_mobile"]

    class Meta:
        verbose_name = 'Врачебная аккредитация'
        verbose_name_plural = 'Врачебные аккредитации'
        ordering = ['-created_at']

    def __str__(self):
        return self.created_at


class DoctorReferral(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название направления")
    description = CKEditor5Field(
        config_name="default",
        blank=True,
        verbose_name="Описание направления",
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = 'Профессиональное направление'
        verbose_name_plural = 'Профессиональные направления'

    def __str__(self):
        return self.title or None


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
        config_name="default",
        blank=True,
        verbose_name="Описание врача",
        null=True
    )

    class Meta:
        verbose_name = 'Информация о сотруднике'
        verbose_name_plural = 'Информация о сотруднике'

    def __str__(self):
        return self.title or None


class DoctorJobResults(models.Model):
    author = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name="Автор работ")
    title = models.CharField(max_length=255, verbose_name="Заголовок описания работы")
    description = CKEditor5Field(
        config_name="default",
        blank=True,
        verbose_name="Описание работы",
        null=True
    )
    photo_before = models.ImageField(
        upload_to="doctors/before", blank=True, null=True, verbose_name="Работа «до»"
    )
    photo_before_mobile = models.ImageField(
            upload_to="doctors/",
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

    IMAGE_VARIANT_FIELDS = ["photo", "photo_mobile"]


    class Meta:
        verbose_name = 'Результат работа сотрудника'
        verbose_name_plural = 'Результат работ сотрудника'
    
    def __str__(self):
        return self.title or None
    