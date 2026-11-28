from typing import Optional

from ninja import Schema

from .default_schemas import PictureFormatSchema, build_picture_format


class OurWorkGallerySchema(Schema):
    poster: Optional[PictureFormatSchema] = None
    size: Optional[str] = None

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)


class OurWorkSectionSchema(Schema):
    title: Optional[str] = None
    posters: Optional[list[OurWorkGallerySchema]] = None

    @staticmethod
    def resolve_posters(obj):
        return obj.ourworkimagegallerymodel_set.order_by("pk")
