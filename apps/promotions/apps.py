from django.apps import AppConfig


class PromotionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.promotions'
    verbose_name = 'Акции'

    def ready(self):
        import apps.promotions.signals  # noqa: F401
