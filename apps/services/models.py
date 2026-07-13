from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class ServiceCategory(ImageVariantsMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    icon = models.ImageField(upload_to='service_categories/', blank=True, verbose_name='Иконка')
    icon_mobile = models.ImageField(
        upload_to='service_categories/', blank=True, verbose_name='Иконка (мобильная версия)',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    IMAGE_VARIANT_FIELDS = ['icon', 'icon_mobile']

    class Meta:
        verbose_name = 'Категория услуг'
        verbose_name_plural = 'Категории услуг'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT,
        related_name='services', verbose_name='Категория',
    )
    description = CKEditor5Field(blank=True, verbose_name='Описание', config_name='default')
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class BranchService(models.Model):
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE,
        related_name='branch_services', verbose_name='Филиал',
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE,
        related_name='branch_services', verbose_name='Услуга',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_from = models.BooleanField(default=False, verbose_name='От (цена примерная)')
    is_active = models.BooleanField(default=True, verbose_name='Активна в филиале')

    class Meta:
        unique_together = ('branch', 'service')
        verbose_name = 'Услуга в филиале'
        verbose_name_plural = 'Услуги в филиалах'

    def __str__(self):
        return f"{self.service} @ {self.branch}"
