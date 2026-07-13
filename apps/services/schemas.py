from ninja import Schema
from decimal import Decimal
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class ServiceCategorySchema(Schema):
    id: int
    name: str
    slug: str
    icon: Optional[PictureFormatSchema] = None

    @staticmethod
    def resolve_icon(obj):
        return build_picture_format(obj.icon, obj.icon_mobile)


class ServiceWithPriceSchema(Schema):
    id: int
    name: str
    slug: str
    category_id: int
    price: Decimal
    price_from: bool
