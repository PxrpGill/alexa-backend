from django.db import models
from django.core.exceptions import ValidationError

from apps.branch.models import BranchModel


class Consultation(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        DONE = "done", "Завершена"

    patient_name = models.CharField(max_length=255, verbose_name="Имя пациента")
    patient_phone = models.CharField(max_length=30, verbose_name="Телефон")
    branch = models.ForeignKey(
        BranchModel, on_delete=models.CASCADE, verbose_name="Филиал"
    )
    page_url = models.CharField(
        verbose_name="Откуда сделана заявка", max_length=255, default="/", blank=True
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
        verbose_name = "Заявки на консультацию"
        verbose_name_plural = "Заявки на консультацию"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient_name} — {self.branch}"
