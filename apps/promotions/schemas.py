from ninja import Schema
from datetime import date
from typing import Optional
from pydantic import model_serializer
from apps.common.schemas.default_schemas import (
    PictureFormatSchema,
    build_picture_format,
)
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
    title: Optional[str] = None
    content: Optional[str] = None


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
    detail: Optional[PromotionDetailSectionSchema] = None
    detail_content: Optional[str] = None
    form: Optional[PromotionFeedbackFormSchema] = None

    @staticmethod
    def resolve_hero(obj):
        return obj

    @staticmethod
    def resolve_detail(obj):
        # CKEditor оставляет в пустых полях разметку вроде "<p>&nbsp;</p>",
        # поэтому пустоту проверяем через has_content, а не по truthiness.
        title = obj.detail_title if has_content(obj.detail_title) else None
        content = (
            obj.detail_description if has_content(obj.detail_description) else None
        )
        if title is None and content is None:
            return None
        return {"title": title, "content": content}

    @staticmethod
    def resolve_form(obj):
        return getattr(obj, "feedback_form", None)

    @staticmethod
    def resolve_detail_content(obj):
        return obj.detail_content if has_content(obj.detail_content) else None

    @model_serializer(mode="wrap")
    def _omit_empty_sections(self, handler):
        """Не отдаём незаполненные секции вовсе, а не как null/пустые строки."""
        data = handler(self)

        detail = data.get("detail")
        if isinstance(detail, dict):
            detail = {key: value for key, value in detail.items() if value is not None}
        if detail:
            data["detail"] = detail
        else:
            data.pop("detail", None)

        if data.get("detail_content") is None:
            data.pop("detail_content", None)

        return data



def _non_empty_rows(rows):
    return [
        row for row in rows if has_content(row.title) or has_content(row.description)
    ]
