from ninja import Router
from typing import Optional
from django.utils import timezone
from django.db.models import Q
from .models import Promotion
from .schemas import PromotionSchema

router = Router(tags=['Акции'])


@router.get('/', response=list[PromotionSchema])
def list_promotions(request, branch_id: Optional[int] = None):
    """Активные акции на сегодняшнюю дату. Фильтр: ?branch_id=<id>."""
    today = timezone.localdate()
    qs = Promotion.objects.filter(
        is_active=True,
        starts_at__lte=today,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=today))

    if branch_id:
        qs = qs.filter(branches__id=branch_id)

    return qs
