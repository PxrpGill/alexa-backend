from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import format_lead_message, queue_max_notification

from .models import PromotionRequests


@receiver(post_save, sender=PromotionRequests)
def on_promotion_request_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новой заявке на акцию."""
    if not created:
        return

    text = format_lead_message(
        "🎁 Новая заявка на акцию",
        [
            ("Имя", instance.patient_name),
            ("Телефон", instance.patient_phone),
            ("Акция", instance.promotion.title if instance.promotion else None),
            (
                "Создана",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
    transaction.on_commit(lambda: queue_max_notification(text))
