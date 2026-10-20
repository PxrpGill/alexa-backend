from django.db.models import Prefetch, Q
from django.utils import timezone
from ninja import Router

from .models import StoryGroup, StoryItem
from .schemas import StoriesSchema

router = Router(tags=["Сторисы"])


@router.get("", response=StoriesSchema, exclude_none=True)
def list_stories(request):
    """Лента сторисов на главной: опубликованные группы с готовыми кадрами."""
    now = timezone.now()
    ready_items = StoryItem.objects.filter(
        processing_status=StoryItem.ProcessingStatus.READY
    )
    groups = (
        StoryGroup.objects.filter(is_published=True)
        .filter(Q(publish_from__isnull=True) | Q(publish_from__lte=now))
        .filter(Q(publish_to__isnull=True) | Q(publish_to__gte=now))
        .filter(items__processing_status=StoryItem.ProcessingStatus.READY)
        .distinct()
        .prefetch_related(Prefetch("items", queryset=ready_items))
    )
    return {"groups": list(groups)}
