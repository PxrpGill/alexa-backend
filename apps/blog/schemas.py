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
    cover: Optional[str] = None
    excerpt: str
    published_at: Optional[datetime] = None

    @staticmethod
    def resolve_cover(obj):
        return obj.cover.url if obj.cover else None


class BlogPostDetailSchema(BlogPostListSchema):
    content: str
