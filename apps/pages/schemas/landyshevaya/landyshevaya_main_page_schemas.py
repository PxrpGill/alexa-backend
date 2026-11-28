from typing import Optional

from ninja import Schema
from pydantic import model_serializer

from apps.common.content import has_content
from apps.common.schemas.cta_section_schemas import CtaSectionSchema
from apps.common.schemas.curators_section_schemas import CuratorsSectionSchema
from apps.common.schemas.faq_section_schemas import FaqSectionSchema
from apps.common.schemas.hero_promotion_schemas import HeroPromotionSlideSchema
from apps.common.schemas.our_work_schemas import OurWorkSectionSchema
from apps.common.schemas.title_description_slider_schemas import (
    TitleDescriptionSlidersSchema,
)


def _prune_empty(value):
    """Убирает пустые значения: разметку CKEditor, пустые строки, списки и объекты."""
    if isinstance(value, str):
        return value if has_content(value) else None
    if isinstance(value, list):
        items = []
        for item in value:
            cleaned = _prune_empty(item)
            if cleaned is not None:
                items.append(cleaned)
        return items or None
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            result = _prune_empty(item)
            if result is not None:
                cleaned[key] = result
        return cleaned or None
    return value


class LandyshevayaMainPageSchema(Schema):
    promotions_slider: Optional[list[HeroPromotionSlideSchema]] = None
    curators_section: Optional[CuratorsSectionSchema] = None
    cta_section: Optional[CtaSectionSchema] = None
    our_work_section: Optional[OurWorkSectionSchema] = None
    title_description_sliders: Optional[TitleDescriptionSlidersSchema] = None
    faq_section: Optional[FaqSectionSchema] = None

    @staticmethod
    def resolve_promotions_slider(obj):
        return obj.hero_slides.filter(is_active=True).order_by("position", "pk")

    @staticmethod
    def resolve_curators_section(obj):
        return getattr(obj, "curatorssectionmodel", None)

    @staticmethod
    def resolve_cta_section(obj):
        return getattr(obj, "ctasectionmodel", None)

    @staticmethod
    def resolve_our_work_section(obj):
        return getattr(obj, "ourworksectionmodel", None)

    @staticmethod
    def resolve_title_description_sliders(obj):
        return getattr(obj, "titledescriptionsliderssectionmodel", None)

    @staticmethod
    def resolve_faq_section(obj):
        return getattr(obj, "faqsectionmodel", None)

    @model_serializer(mode="wrap")
    def _omit_empty_sections(self, handler):
        """Не отдаём пустые поля/секции: null, "", "<p>&nbsp;</p>", [], {}."""
        return _prune_empty(handler(self)) or {}
