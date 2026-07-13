from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class Specialization(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')

    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(ImageVariantsMixin, models.Model):
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    patronymic = models.CharField(max_length=100, verbose_name='Отчество')
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True, verbose_name='Фото')
    photo_mobile = models.ImageField(
        upload_to='doctors/', blank=True, null=True,
        verbose_name='Фото (мобильная версия)',
    )
    bio = CKEditor5Field(blank=True, verbose_name='Биография', config_name='default')
    specializations = models.ManyToManyField(
        Specialization, blank=True, verbose_name='Специализации'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    IMAGE_VARIANT_FIELDS = ['photo', 'photo_mobile']

    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"


class DoctorBranch(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Врач')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, verbose_name='Филиал')
    schedule = models.JSONField(default=dict, blank=True, verbose_name='Расписание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Врач в филиале'
        verbose_name_plural = 'Врачи в филиалах'
        unique_together = [('doctor', 'branch')]
