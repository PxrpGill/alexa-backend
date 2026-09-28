from django.apps import AppConfig


class DmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dms'
    verbose_name = 'Заявки ДМС'

    def ready(self):
        import apps.dms.signals  # noqa: F401
