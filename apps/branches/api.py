from ninja import Router
from django.shortcuts import get_object_or_404
from .models import Branch
from .schemas import BranchSchema

router = Router(tags=['Филиалы'])


@router.get('/', response=list[BranchSchema])
def list_branches(request):
    """Список активных филиалов клиники."""
    return Branch.objects.filter(is_active=True)


@router.get('/{branch_id}/', response=BranchSchema)
def get_branch(request, branch_id: int):
    """Информация о филиале по ID. 404 если филиал неактивен."""
    return get_object_or_404(Branch, id=branch_id, is_active=True)
