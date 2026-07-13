from ninja import Schema
from datetime import datetime
from typing import Optional


class BlogCategorySchema(Schema):
    id: int
    name: str
    slug: str


class BlogPostListSchema(Schema):
    id: int
    title: str
    slug: str
    category: BlogCategorySchema
    previewPoster: Optional[str] = None
    poster: Optional[str] = None
    description: str
    publishDate: Optional[datetime] = None

    @staticmethod
    def resolve_previewPoster(obj):
        return obj.preview_poster.url if obj.preview_poster else None

    @staticmethod
    def resolve_poster(obj):
        return obj.poster.url if obj.poster else None

    @staticmethod
    def resolve_publishDate(obj):
        return obj.published_at


class BlogPostDetailSchema(BlogPostListSchema):
    content: str


class PaginatedBlogPostSchema(Schema):
    items: list[BlogPostListSchema]
    page: int
    perPage: int
    total: int
    totalPages: int
