from ninja import Schema
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class SpecializationSchema(Schema):
    id: int
    name: str


class DoctorSchema(Schema):
    id: int
    first_name: str
    last_name: str
    patronymic: str
    photo: Optional[PictureFormatSchema] = None
    bio: str
    specializations: list[SpecializationSchema]
    is_active: bool

    @staticmethod
    def resolve_photo(obj):
        return build_picture_format(obj.photo, obj.photo_mobile)
