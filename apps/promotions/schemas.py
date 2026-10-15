from ninja import Schema
from datetime import date
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format
from apps.promotions.content import has_content


class PromotionSchema(Schema):
    slug: str
    title: str
    description: Optional[str]
    banner: Optional[PictureFormatSchema] = None
    starts_at: date
    ends_at: Optional[date] = None
    is_active: bool

    @staticmethod
    def resolve_banner(obj):
        return build_picture_format(obj.banner, obj.banner_mobile)


class PromotionRequestSchema(Schema):
    slug: str
    patient_name: str
    patient_phone: str
    is_ad_agreement: Optional[bool] = None
    is_privacy_agreement: Optional[bool] = None


class PromotionDetailSectionSchema(Schema):
    title: str
    content: str


class PromotionConditionCardSchema(Schema):
    icon: str
    title: str
    description: str

    @staticmethod
    def resolve_icon(obj):
        """Иконка отдаётся исходным файлом (в т.ч. SVG), без webp/avif-вариантов."""
        return obj.icon.url if obj.icon else ""


class PromotionConditionsSchema(Schema):
    title: str
    cards: list[PromotionConditionCardSchema]

    @staticmethod
    def resolve_title(obj):
        return obj.conditions_title

    @staticmethod
    def resolve_cards(obj):
        return obj.conditions.all()


class PromotionTitleDescriptionSchema(Schema):
    title: str
    description: str


class PromotionDetailSchema(Schema):
    slug: str
    hero: PromotionSchema
    detail: PromotionDetailSectionSchema
    conditions: PromotionConditionsSchema
    target_audience: Optional[list[PromotionTitleDescriptionSchema]]
    what_promotion_include: Optional[list[PromotionTitleDescriptionSchema]]
    why_it_matters: Optional[list[PromotionTitleDescriptionSchema]]

    @staticmethod
    def resolve_hero(obj):
        return obj

    @staticmethod
    def resolve_detail(obj):
        return {"title": obj.detail_title, "content": obj.detail_description}

    @staticmethod
    def resolve_conditions(obj):
        return obj

    @staticmethod
    def resolve_target_audience(obj):
        return _non_empty_rows(obj.target_audience.all())

    @staticmethod
    def resolve_what_promotion_include(obj):
        return _non_empty_rows(obj.promotion_include.all())

    @staticmethod
    def resolve_why_it_matters(obj):
        return _non_empty_rows(obj.why_it_matters.all())


def _non_empty_rows(rows):
    return [row for row in rows if has_content(row.title) or has_content(row.description)]
