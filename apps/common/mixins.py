from apps.common.images import generate_image_variants


class ImageVariantsMixin:
    """Модель объявляет IMAGE_VARIANT_FIELDS — список имён ImageField.
    После сохранения для каждого непустого поля из списка генерируются
    .webp/.avif варианты (см. apps.common.images.generate_image_variants).
    """

    IMAGE_VARIANT_FIELDS = []

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for field_name in self.IMAGE_VARIANT_FIELDS:
            field_file = getattr(self, field_name)
            if field_file:
                generate_image_variants(field_file)
