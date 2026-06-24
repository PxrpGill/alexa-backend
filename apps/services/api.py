from ninja import Router
from typing import Optional
from .models import ServiceCategory, BranchService
from .schemas import ServiceCategorySchema, ServiceWithPriceSchema

router = Router(tags=['Services'])


@router.get('/categories/', response=list[ServiceCategorySchema])
def list_categories(request):
    return ServiceCategory.objects.all()


@router.get('/', response=list[ServiceWithPriceSchema])
def list_services(request, branch_id: Optional[int] = None, category: Optional[str] = None):
    qs = BranchService.objects.filter(
        is_active=True, service__is_active=True,
    ).select_related('service', 'service__category')
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if category:
        qs = qs.filter(service__category__slug=category)

    return [
        ServiceWithPriceSchema(
            id=bs.service.id,
            name=bs.service.name,
            slug=bs.service.slug,
            category_id=bs.service.category_id,
            price=bs.price,
            price_from=bs.price_from,
        )
        for bs in qs
    ]
