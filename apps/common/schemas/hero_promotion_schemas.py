from typing import Optional

from ninja import Schema

from .default_schemas import PictureFormatSchema, build_picture_format
from .site_button_schemas import SiteButtonSchema


class HeroPromotionSlideCardSchema(Schema):
    title: Optional[str] = None
    content: Optional[str] = None
    button: Optional[SiteButtonSchema] = None

    @staticmethod
    def resolve_button(obj):
        # Кнопка не отдельная модель: её поля лежат прямо на карточке.
        return obj


class HeroPromotionSlideSchema(Schema):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    legend: Optional[str] = None
    position: int
    text_theme: Optional[str] = None

    poster: Optional[PictureFormatSchema] = None
    card: Optional[HeroPromotionSlideCardSchema] = None

    @staticmethod
    def resolve_poster(obj):
        # build_picture_format сам кладёт мобильную версию в поле mobile.
        return build_picture_format(obj.poster, obj.poster_mobile)

    @staticmethod
    def resolve_card(obj):
        # reverse OneToOne: если карточки нет, Django бросает
        # RelatedObjectDoesNotExist (это подкласс AttributeError).
        return getattr(obj, "card", None)
