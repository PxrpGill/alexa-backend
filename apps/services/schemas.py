from ninja import Schema
from decimal import Decimal
from typing import Optional


class ServiceCategorySchema(Schema):
    id: int
    name: str
    slug: str
    icon: Optional[str] = None

    @staticmethod
    def resolve_icon(obj):
        return obj.icon.url if obj.icon else None


class ServiceWithPriceSchema(Schema):
    id: int
    name: str
    slug: str
    category_id: int
    price: Decimal
    price_from: bool
