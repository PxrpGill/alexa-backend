from ninja import Schema
from datetime import date
from typing import Optional


class PromotionSchema(Schema):
    id: int
    title: str
    banner: Optional[str] = None
    starts_at: date
    ends_at: Optional[date] = None
    is_active: bool

    @staticmethod
    def resolve_banner(obj):
        return obj.banner.url if obj.banner else None
