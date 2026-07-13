import logging

from apps.common.tasks import generate_image_variants_task

logger = logging.getLogger(__name__)


class ImageVariantsMixin:
    """Модель объявляет IMAGE_VARIANT_FIELDS — список имён ImageField.
    После сохранения для каждого непустого поля из списка асинхронно ставится
    задача генерации .webp/.avif вариантов (apps.common.tasks.generate_image_variants_task).
    Если постановка в очередь не удалась (брокер недоступен) — save() всё равно
    завершается успешно, ошибка только логируется.
    """

    IMAGE_VARIANT_FIELDS = []

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for field_name in self.IMAGE_VARIANT_FIELDS:
            field_file = getattr(self, field_name)
            if not field_file:
                continue
            try:
                generate_image_variants_task.delay(
                    self._meta.app_label, self.__class__.__name__, self.pk, field_name,
                )
            except Exception:
                logger.exception(
                    'Не удалось поставить в очередь генерацию вариантов изображения '
                    '(%s.%s, pk=%s, field=%s)',
                    self._meta.app_label, self.__class__.__name__, self.pk, field_name,
                )
