from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.appointments'
    verbose_name = 'Записи на приём'

    def ready(self):
        import apps.appointments.signals  # noqa: F401
