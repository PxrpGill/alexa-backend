from typing import Optional

from ninja import Schema

from .default_schemas import PictureFormatSchema, build_picture_format


class TitleDescriptionSliderGallerySchema(Schema):
    poster: Optional[PictureFormatSchema] = None

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)


class TitleDescriptionSliderSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    gallery: Optional[list[TitleDescriptionSliderGallerySchema]] = None

    @staticmethod
    def resolve_gallery(obj):
        return obj.titledescriptionslidegallerymodel_set.order_by("pk")


class TitleDescriptionSlidersSchema(Schema):
    title: Optional[str] = None
    sliders: Optional[list[TitleDescriptionSliderSchema]] = None

    @staticmethod
    def resolve_sliders(obj):
        return obj.titledescriptionslidemodel_set.order_by("pk")
