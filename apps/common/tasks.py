from celery import shared_task

from apps.common.images import generate_image_variants


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def generate_image_variants_task(app_label, model_name, pk, field_name):
    from django.apps import apps

    model = apps.get_model(app_label, model_name)
    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return

    field_file = getattr(instance, field_name)
    if field_file:
        generate_image_variants(field_file)
