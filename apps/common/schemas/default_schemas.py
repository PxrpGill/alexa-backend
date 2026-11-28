import os
from typing import Optional

from ninja import Schema


class SuccessResponseMessageSchema(Schema):
    message: str


class ErrorResponseMessageSchema(Schema):
    message: str


class PictureFormatDataSchema(Schema):
    src: str
    mobile: Optional[str] = None


class PictureFormatSchema(Schema):
    original: Optional[PictureFormatDataSchema] = None
    webp: Optional[PictureFormatDataSchema] = None
    avif: Optional[PictureFormatDataSchema] = None


def _resolve_variant_url(field_file, extension):
    storage = field_file.storage
    base, _ext = os.path.splitext(field_file.name)
    name = f'{base}.{extension}'
    if not storage.exists(name):
        return None
    return storage.url(name)


def build_picture_format(src_field, mobile_field=None):
    if not src_field:
        return None

    mobile_original = mobile_field.url if mobile_field else None
    data = {
        'original': PictureFormatDataSchema(src=src_field.url, mobile=mobile_original),
    }

    for extension in ('webp', 'avif'):
        variant_src = _resolve_variant_url(src_field, extension)
        if variant_src is None:
            continue
        variant_mobile = _resolve_variant_url(mobile_field, extension) if mobile_field else None
        data[extension] = PictureFormatDataSchema(src=variant_src, mobile=variant_mobile)

    return PictureFormatSchema(**data)
