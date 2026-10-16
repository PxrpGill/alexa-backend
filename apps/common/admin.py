"""Общие помощники для admin-панели."""

from django.contrib import admin
from django.utils.html import format_html

PREVIEW_HEIGHT = 72


def make_image_preview(field_name, label="Превью", height=PREVIEW_HEIGHT):
    """Возвращает readonly-колонку с миниатюрой картинки.

    Годится и для `list_display`, и для `readonly_fields` формы или inline:
    редактор видит, какой файл лежит в поле, а не только путь к нему.
    Пустое поле отдаёт прочерк. Файл берётся «как есть» (без webp/avif-вариантов):
    в админке важна узнаваемость, а не вес картинки.
    """

    @admin.display(description=label)
    def preview(_model_admin, obj):
        image = getattr(obj, field_name, None)
        if not image:
            return "—"
        return format_html(
            '<img src="{}" class="admin-image-preview" style="height: {}px" '
            'alt="" loading="lazy">',
            image.url,
            height,
        )

    preview.__name__ = f"{field_name}_preview"
    return preview
