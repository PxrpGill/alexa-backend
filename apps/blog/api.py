from ninja import Router
from django.shortcuts import get_object_or_404
from .models import BlogPost
from .schemas import BlogPostListSchema, BlogPostDetailSchema

router = Router(tags=['Blog'])


@router.get('/', response=list[BlogPostListSchema])
def list_posts(request):
    return BlogPost.objects.filter(
        status=BlogPost.Status.PUBLISHED
    ).select_related('category')


@router.get('/{slug}/', response=BlogPostDetailSchema)
def get_post(request, slug: str):
    return get_object_or_404(BlogPost, slug=slug, status=BlogPost.Status.PUBLISHED)
