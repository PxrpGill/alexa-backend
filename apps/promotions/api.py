from ninja import Router
from django.utils import timezone
from django.db.models import Q
from .models import Promotion
from .schemas import PromotionSchema

router = Router(tags=['Акции'])


@router.get('', response=list[PromotionSchema])
def list_promotions(request):
    """Активные акции на сегодняшнюю дату."""
    today = timezone.localdate()
    return Promotion.objects.filter(
        is_active=True,
        starts_at__lte=today,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=today))