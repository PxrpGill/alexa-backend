from typing import Optional

from ninja import Schema

from .default_schemas import PictureFormatSchema, build_picture_format


class CuratorsSectionSchema(Schema):
    poster: Optional[PictureFormatSchema] = None

    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)
