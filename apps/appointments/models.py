from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'in_progress', 'В обработке'
        DONE = 'done', 'Завершена'

    patient_name = models.CharField(max_length=255, verbose_name='Имя пациента')
    patient_phone = models.CharField(max_length=30, verbose_name='Телефон')
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.PROTECT,
        related_name='appointments', verbose_name='Филиал',
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='appointments', verbose_name='Врач',
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='appointments', verbose_name='Услуга',
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, verbose_name='Статус',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.patient_name} — {self.branch.name}'
