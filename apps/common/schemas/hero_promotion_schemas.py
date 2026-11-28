from typing import Optional
from ninja import Schema

from .site_button_schemas import SiteButtonSchema
from .default_schemas import PictureFormatSchema, build_picture_format


class HeroPromotionSlideCardSchema(Schema):
    title: Optional[str]
    content: Optional[str]
    button: Optional[SiteButtonSchema]


class HeroPromotionSlideSchema(Schema):
    title: Optional[str]
    subtitle: Optional[str]
    legend: Optional[str]
    position: int
    text_theme: str

    poster: Optional[PictureFormatSchema] = None
    poster_mobile: Optional[PictureFormatSchema] = None

    position: int

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)
