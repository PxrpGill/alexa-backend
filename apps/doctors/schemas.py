from ninja import Schema
from typing import Optional


class SpecializationSchema(Schema):
    id: int
    name: str


class DoctorSchema(Schema):
    id: int
    first_name: str
    last_name: str
    patronymic: str
    photo: Optional[str] = None
    bio: str
    specializations: list[SpecializationSchema]
    is_active: bool

    @staticmethod
    def resolve_photo(obj):
        if obj.photo:
            return obj.photo.url
        return None
