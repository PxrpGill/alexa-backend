from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import queue_lead_notification

from .models import DMS


@receiver(post_save, sender=DMS)
def on_dms_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новой заявке ДМС."""
    if not created:
        return

    queue_lead_notification(
        "🏥 Новая заявка ДМС",
        [
            ("Имя", instance.patient_name),
            ("Телефон", instance.patient_phone),
            ("Филиал", instance.branch.name if instance.branch else None),
            ("Страница", instance.page_url),
            (
                "Создана",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
