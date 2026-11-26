from ninja import Schema
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class DoctorSchema(Schema):
    full_name: str
    photo: Optional[PictureFormatSchema] = None
    is_active: bool

    @staticmethod
    def resolve_photo(obj):
        return build_picture_format(obj.photo, obj.photo_mobile)
