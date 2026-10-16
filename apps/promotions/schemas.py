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


class PromotionFeedbackFormSchema(Schema):
    title: str
    description: Optional[str] = None
    button_text: Optional[str] = None

    @staticmethod
    def resolve_description(obj):
        return obj.description or None

    @staticmethod
    def resolve_button_text(obj):
        return obj.button_text or None


class PromotionDetailSchema(Schema):
    slug: str
    hero: PromotionSchema
    detail: PromotionDetailSectionSchema
    detail_content: Optional[str] = None
    form: Optional[PromotionFeedbackFormSchema] = None

    @staticmethod
    def resolve_hero(obj):
        return obj

    @staticmethod
    def resolve_detail(obj):
        return {"title": obj.detail_title, "content": obj.detail_description}

    @staticmethod
    def resolve_form(obj):
        return getattr(obj, "feedback_form", None)

    @staticmethod
    def resolve_detail_content(obj):
        return obj.detail_content or None


def _non_empty_rows(rows):
    return [
        row for row in rows if has_content(row.title) or has_content(row.description)
    ]
