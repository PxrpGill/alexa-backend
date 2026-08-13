from django.core.exceptions import ValidationError
from django.db import models

from apps.branch.models import BranchModel


class Appointment(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        DONE = "done", "Завершена"

    patient_name = models.CharField(max_length=255, verbose_name="Имя пациента")
    patient_phone = models.CharField(max_length=30, verbose_name="Телефон")
    branch = models.ForeignKey(
        BranchModel, on_delete=models.CASCADE, verbose_name="Филиал", null=True
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Запись на приём"
        verbose_name_plural = "Записи на приём"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient_name} — {self.branch}"
