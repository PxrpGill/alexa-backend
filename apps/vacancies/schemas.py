from typing import Optional

from ninja import Schema

from apps.common.schemas import PictureFormatSchema, build_picture_format

from .models import VacancyRequirement


class VacancyCategorySchema(Schema):
    slug: str
    name: str


class VacancyListSchema(Schema):
    slug: str
    vacancy_name: str
    description: str
    branch: str

    @staticmethod
    def resolve_vacancy_name(obj):
        return obj.name

    @staticmethod
    def resolve_branch(obj):
        return obj.branch.slug


class VacanciesListResponseSchema(Schema):
    categories: list[VacancyCategorySchema]
    results: list[VacancyListSchema]
    total: int


class HeroSchema(Schema):
    vacancy_name: str
    description: str
    badges: list[str]

    @staticmethod
    def resolve_vacancy_name(obj):
        return obj.name

    @staticmethod
    def resolve_badges(obj):
        return [badge.text for badge in obj.badges.all()]


class RequirementCardSchema(Schema):
    icon: str
    title: str
    description: str

    @staticmethod
    def resolve_icon(obj):
        return obj.icon.url if obj.icon else ""


class RequirementGroupSchema(Schema):
    title: str
    cards: list[RequirementCardSchema]


class RequirementsSchema(Schema):
    required: RequirementGroupSchema
    partial: RequirementGroupSchema

    @staticmethod
    def resolve_required(obj):
        cards = [
            card
            for card in obj.requirements.all()
            if card.type == VacancyRequirement.Type.REQUIRED
        ]
        return {"title": obj.requirements_title, "cards": cards}

    @staticmethod
    def resolve_partial(obj):
        cards = [
            card
            for card in obj.requirements.all()
            if card.type == VacancyRequirement.Type.PARTIAL
        ]
        return {"title": obj.partial_requirements_title, "cards": cards}


class ResponsibilityCardSchema(Schema):
    image: Optional[PictureFormatSchema] = None
    title: str
    description: str

    @staticmethod
    def resolve_image(obj):
        return build_picture_format(obj.image)


class ResponsibilitiesSchema(Schema):
    title: str
    cards: list[ResponsibilityCardSchema]

    @staticmethod
    def resolve_title(obj):
        return obj.responsibilities_title

    @staticmethod
    def resolve_cards(obj):
        return obj.responsibilities.all()


class BenefitCardSchema(Schema):
    title: str
    description: str


class BenefitImageSchema(Schema):
    image: Optional[PictureFormatSchema] = None
    alt: str

    @staticmethod
    def resolve_image(obj):
        return build_picture_format(obj.image)


class WhatYouWillGetSchema(Schema):
    images: list[BenefitImageSchema]
    cards: list[BenefitCardSchema]

    @staticmethod
    def resolve_images(obj):
        return obj.benefit_images.all()

    @staticmethod
    def resolve_cards(obj):
        return obj.benefits.all()


class VacancyDetailSchema(Schema):
    slug: str
    hero: HeroSchema
    what_you_will_get: WhatYouWillGetSchema
    requirements: RequirementsSchema
    responsibilities: ResponsibilitiesSchema

    @staticmethod
    def resolve_hero(obj):
        return obj

    @staticmethod
    def resolve_what_you_will_get(obj):
        return obj

    @staticmethod
    def resolve_requirements(obj):
        return obj

    @staticmethod
    def resolve_responsibilities(obj):
        return obj


class ApplicationCreateSchema(Schema):
    name: Optional[str] = None
    phone: Optional[str] = None
    privacy_policy_accepted: Optional[bool] = None


class ApplicationErrorSchema(Schema):
    name: Optional[list[str]] = None
    phone: Optional[list[str]] = None
    resume: Optional[list[str]] = None
    privacy_policy_accepted: Optional[list[str]] = None
