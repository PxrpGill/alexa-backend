from ninja import Schema
from datetime import date
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class PromotionSchema(Schema):
    id: int
    title: str
    banner: Optional[PictureFormatSchema] = None
    starts_at: date
    ends_at: Optional[date] = None
    is_active: bool

    @staticmethod
    def resolve_banner(obj):
        return build_picture_format(obj.banner, obj.banner_mobile)
