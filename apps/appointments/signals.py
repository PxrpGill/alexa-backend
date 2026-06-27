from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment


def notify_telegram(appointment: Appointment) -> None:
    """Stub — implement when Telegram bot is connected."""
    pass


@receiver(post_save, sender=Appointment)
def on_appointment_created(sender, instance, created, **kwargs):
    if created:
        notify_telegram(instance)
