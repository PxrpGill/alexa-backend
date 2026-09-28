from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import queue_lead_notification

from .models import Application


@receiver(post_save, sender=Application)
def on_application_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новом отклике на вакансию."""
    if not created:
        return

    queue_lead_notification(
        "📄 Новый отклик на вакансию",
        [
            ("Имя", instance.name),
            ("Телефон", instance.phone),
            ("Вакансия", instance.vacancy.name if instance.vacancy else None),
            ("Резюме", "приложено" if instance.resume else "нет"),
            (
                "Создан",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
