import os
from io import BytesIO

import pillow_avif  # noqa: F401  — регистрирует кодек AVIF в Pillow
from django.core.files.base import ContentFile
from PIL import Image

WEBP_QUALITY = 85
AVIF_QUALITY = 60

_VARIANTS = (
    ('webp', 'WEBP', WEBP_QUALITY),
    ('avif', 'AVIF', AVIF_QUALITY),
)


def generate_image_variants(field_file):
    """Генерирует .webp и .avif рядом с оригиналом в том же storage.

    field_file — любой объект с атрибутами .storage (Django Storage) и .name
    (относительный путь), т.е. Django FieldFile или совместимый duck-type.
    Идемпотентно: если оба варианта уже существуют для текущего .name — no-op.
    """
    storage = field_file.storage
    base, _ext = os.path.splitext(field_file.name)
    variant_names = {ext: f'{base}.{ext}' for ext, _, _ in _VARIANTS}

    if all(storage.exists(name) for name in variant_names.values()):
        return

    with storage.open(field_file.name, 'rb') as source:
        image = Image.open(source)
        image.load()

    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        image = image.convert('RGBA')
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    for ext, pillow_format, quality in _VARIANTS:
        _save_variant(storage, variant_names[ext], image, pillow_format, quality)


def _save_variant(storage, name, image, pillow_format, quality):
    buffer = BytesIO()
    image.save(buffer, format=pillow_format, quality=quality)
    buffer.seek(0)
    if storage.exists(name):
        storage.delete(name)
    storage.save(name, ContentFile(buffer.read()))
