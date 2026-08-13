from ninja import Router

from .models import BranchModel
from .schema import BranchesGetResponse

router = Router(tags=["Филиалы"])


@router.get("", response={200: list[BranchesGetResponse]})
def get_all_branches(request):
    return BranchModel.objects.all()
