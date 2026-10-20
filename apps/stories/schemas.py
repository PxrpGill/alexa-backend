from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from ninja import Schema
from pydantic import Field

from apps.common.schemas import PictureFormatSchema, build_picture_format

from .media import get_mobile_copy
from .models import StoryItem


class StoryVideoSourceSchema(Schema):
    src: str
    mobile: Optional[str] = None


class StoryImageItemSchema(Schema):
    id: int
    type: Literal["image"]
    poster: PictureFormatSchema
    duration: Optional[int] = None


class StoryVideoItemSchema(Schema):
    id: int
    type: Literal["video"]
    source: StoryVideoSourceSchema
    posterSrc: Optional[str] = None


StoryItemSchema = Annotated[
    Union[StoryImageItemSchema, StoryVideoItemSchema],
    Field(discriminator="type"),
]


class StoryGroupSchema(Schema):
    id: int
    title: Optional[str] = None
    updatedAt: datetime
    preview: Optional[PictureFormatSchema] = None
    items: list[StoryItemSchema]

    @staticmethod
    def resolve_title(obj):
        return obj.title or None

    @staticmethod
    def resolve_updatedAt(obj):
        return obj.updated_at

    @staticmethod
    def resolve_preview(obj):
        return build_story_picture(obj.preview)

    @staticmethod
    def resolve_items(obj):
        return [serialize_story_item(item) for item in obj.items.all()]


class StoriesSchema(Schema):
    groups: list[StoryGroupSchema]


def build_story_picture(field_file):
    """PictureFormatSchema, где mobile — сгенерированная копия до 750 px."""
    return build_picture_format(field_file, get_mobile_copy(field_file))


def serialize_story_item(item):
    if item.type == StoryItem.Type.VIDEO:
        return {
            "id": item.id,
            "type": "video",
            "source": {
                "src": item.video_src.url,
                "mobile": item.video_mobile.url if item.video_mobile else None,
            },
            "posterSrc": item.video_poster.url if item.video_poster else None,
        }
    return {
        "id": item.id,
        "type": "image",
        "poster": build_story_picture(item.image),
        "duration": item.duration,
    }
