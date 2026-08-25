import uuid
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin
from django.utils.text import slugify
from django.db.models import Q
from pytils.translit import slugify as t_slugify


class Promotion(ImageVariantsMixin, models.Model):
    slug = models.SlugField(
        unique=True, verbose_name="Текстовый идентификатор акции", blank=True
    )
    title = models.CharField(max_length=500, verbose_name="Заголовок")
    description = CKEditor5Field(
        config_name="default", blank=True, verbose_name="Описание"
    )
    banner = models.ImageField(
        upload_to="promotions/", blank=True, verbose_name="Баннер"
    )
    banner_mobile = models.ImageField(
        upload_to="promotions/",
        blank=True,
        verbose_name="Баннер (мобильная версия)",
    )
    starts_at = models.DateField(verbose_name="Начало")
    ends_at = models.DateField(null=True, blank=True, verbose_name="Окончание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    IMAGE_VARIANT_FIELDS = ["banner", "banner_mobile"]

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ["-starts_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(t_slugify(self.title)) or f"promotion-{uuid.uuid4().hex[:8]}"
            slug = base
            counter = 1

            while Promotion.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1

            self.slug = slug

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PromotionRequests(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        DONE = "done", "Завершена"

    patient_name = models.CharField(max_length=255, verbose_name="Имя пациента")
    patient_phone = models.CharField(max_length=30, verbose_name="Телефон")
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, verbose_name="Выбранные акции"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Статус",
    )
    is_ad_agreement = models.BooleanField(
        default=False,
        verbose_name="Согласие на получение рассылки рекламно-информационных материалов",
        null=True,
    )
    is_privacy_agreement = models.BooleanField(
        default=False,
        verbose_name="Согласие на политику конфиденциальности",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Заявки на акцию"
        verbose_name_plural = "Заявки на акции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient_name}"
