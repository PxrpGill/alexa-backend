from ninja import Router
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .models import BlogPost
from .schemas import BlogPostDetailSchema, PaginatedBlogPostSchema

router = Router(tags=["Блог"])

DEFAULT_PER_PAGE = 10


@router.get("", response=PaginatedBlogPostSchema)
def list_posts(
    request, page: int = 1, perPage: int = DEFAULT_PER_PAGE, allPages: bool = False
):
    """Список опубликованных статей блога с пагинацией."""
    qs = BlogPost.objects.filter(status=BlogPost.Status.PUBLISHED).select_related(
        "category"
    )
    total = qs.count()

    if allPages:
        return {
            "items": list(qs),
            "pagination": {
                "page": 1,
                "perPage": total or 1,
                "total": total,
                "totalPages": 1,
            },
        }

    paginator = Paginator(qs, perPage)
    page_obj = paginator.get_page(page)
    
    return {
        "items": list(page_obj.object_list),
        "pagination": {
            "page": page_obj.number,
            "perPage": perPage,
            "total": total,
            "totalPages": paginator.num_pages,
        },
    }


@router.get("/{slug}", response=BlogPostDetailSchema)
def get_post(request, slug: str):
    """Статья блога по slug. 404 если не опубликована."""
    return get_object_or_404(BlogPost, slug=slug, status=BlogPost.Status.PUBLISHED)
