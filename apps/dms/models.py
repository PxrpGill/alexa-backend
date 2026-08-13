from django.db import models
from django.core.exceptions import ValidationError


class DMS(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        DONE = "done", "Завершена"

    class Branch(models.TextChoices):
        LANDYSHEVAYA = "Landyshevaya 104", "Ландышевая 104"
        VOLKOVA = "Volkova 22", "Волкова 22"

    patient_name = models.CharField(max_length=255, verbose_name="Имя пациента")
    patient_phone = models.CharField(max_length=30, verbose_name="Телефон")
    branch_name = models.CharField(
        verbose_name="Название филиала",
        choices=Branch.choices,
        default=Branch.LANDYSHEVAYA,
        max_length=32,
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
        verbose_name = "Заявки ДМС"
        verbose_name_plural = "Заявки ДМС"
        ordering = ["-created_at"]

    def clean(self):
        if self.branch_name not in self.Branch.values:
            raise ValidationError(
                {
                    "branch_name": f"Неизвестный филиал: {self.branch_name}. "
                    f'Допустимые значения: {", ".join(self.Branch.values)}.'
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_name} — {self.branch_name}"
