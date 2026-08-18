from ninja import Schema
from datetime import datetime
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class BlogCategorySchema(Schema):
    id: int
    name: str
    slug: str


class BlogPostListSchema(Schema):
    id: int
    title: str
    slug: str
    category: BlogCategorySchema
    previewPoster: Optional[PictureFormatSchema] = None
    poster: Optional[PictureFormatSchema] = None
    description: str
    publishDate: Optional[datetime] = None

    @staticmethod
    def resolve_previewPoster(obj):
        return build_picture_format(obj.preview_poster, obj.preview_poster_mobile)

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)

    @staticmethod
    def resolve_publishDate(obj):
        return obj.published_at


class BlogPostDetailSchema(BlogPostListSchema):
    content: str


class PaginationSchema(Schema):
    page: int
    perPage: int
    total: int
    totalPages: int


class PaginatedBlogPostSchema(Schema):
    items: list[BlogPostListSchema]
    pagination: PaginationSchema
