from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class Promotion(ImageVariantsMixin, models.Model):
    title = models.CharField(max_length=500, verbose_name='Заголовок')
    description = CKEditor5Field(config_name='default', blank=True, verbose_name='Описание')
    banner = models.ImageField(upload_to='promotions/', blank=True, verbose_name='Баннер')
    banner_mobile = models.ImageField(
        upload_to='promotions/', blank=True, verbose_name='Баннер (мобильная версия)',
    )
    starts_at = models.DateField(verbose_name='Начало')
    ends_at = models.DateField(null=True, blank=True, verbose_name='Окончание')
    branches = models.ManyToManyField(
        'branches.Branch', blank=True,
        related_name='promotions', verbose_name='Филиалы',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    IMAGE_VARIANT_FIELDS = ['banner', 'banner_mobile']

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'
        ordering = ['-starts_at']

    def __str__(self):
        return self.title
