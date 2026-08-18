from django.http import HttpRequest
from ninja import Router
from django.shortcuts import get_object_or_404

from apps.branch.models import BranchModel

from .models import Appointment
from .schemas import AppointmentCreateSchema
from ..common.schemas import SuccessResponseMessageSchema, ErrorResponseMessageSchema

router = Router(tags=["Запись на приём"])


@router.post(
    "/", response={201: SuccessResponseMessageSchema, 400: ErrorResponseMessageSchema}
)
def create_appointment(request: HttpRequest, payload: AppointmentCreateSchema):
    """Создать запись на приём. Возвращает созданную запись (201)."""

    if not payload.is_privacy_agreement:
        return 400, {
            "message": "Невозможно создать заявку без согласия с политикой конфиденциальности"
        }

    branch = get_object_or_404(BranchModel, slug=payload.branch_slug)

    try:
        Appointment.objects.create(
            patient_name=payload.patient_name,
            patient_phone=payload.patient_phone,
            branch=branch,
            page_url=(
                request.build_absolute_uri(payload.page_url)
                if payload.page_url
                else "/"
            ),
            is_ad_agreement=payload.is_ad_agreement,
            is_privacy_agreement=payload.is_privacy_agreement,
        )

        return 201, {"message": "Запись на прием создана"}
    except Exception:
        return 400, {"message": "Некорректные данные при отправке"}
