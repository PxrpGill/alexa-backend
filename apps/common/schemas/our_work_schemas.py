from typing import Optional
from ninja import Schema

from .default_schemas import PictureFormatSchema, build_picture_format


class OurWorkGallerySchema(Schema):
    poster: Optional[PictureFormatSchema]
    poster_mobile: Optional[PictureFormatSchema]
    size: str

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)


class OurWorkSectionSchema(Schema):
    title: Optional[str]
    posters: Optional[OurWorkGallerySchema]
