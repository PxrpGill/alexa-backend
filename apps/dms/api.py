from ninja import Router
from django.shortcuts import get_object_or_404

from apps.branch.models import BranchModel

from .models import DMS
from .schemas import DMSCreateSchema
from ..common.schemas import SuccessResponseMessageSchema, ErrorResponseMessageSchema

router = Router(tags=["Запись на приём"])


@router.post(
    "/", response={201: SuccessResponseMessageSchema, 400: ErrorResponseMessageSchema}
)
def create_appointment(request, payload: DMSCreateSchema):
    """Создать запись ДМС. Возвращает созданную запись (201)."""

    branch = get_object_or_404(BranchModel, slug=payload.branch_slug)

    DMS.objects.create(
        patient_name=payload.patient_name,
        patient_phone=payload.patient_phone,
        page_url=(
            request.build_absolute_uri(payload.page_url) if payload.page_url else "/"
        ),
        branch=branch,
    )

    return 201, {"message": "Запись дмс создана"}
