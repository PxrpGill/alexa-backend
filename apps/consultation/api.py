from ninja import Router
from django.shortcuts import get_object_or_404

from apps.branch.models import BranchModel

from .models import Consultation
from .schemas import ConsultationCreateSchema
from ..common.leads import build_page_url
from ..common.throttling import throttle_lead_form
from ..common.schemas import SuccessResponseMessageSchema, ErrorResponseMessageSchema

router = Router(tags=["Запись на приём"])


@router.post(
    "",
    response={
        201: SuccessResponseMessageSchema,
        400: ErrorResponseMessageSchema,
        429: ErrorResponseMessageSchema,
    },
)
@throttle_lead_form
def create_appointment(request, payload: ConsultationCreateSchema):
    """Создать запись ДМС. Возвращает созданную запись (201)."""

    if not payload.is_privacy_agreement:
        return 400, {
            "message": "Невозможно создать заявку без согласия с политикой конфиденциальности"
        }

    branch = get_object_or_404(BranchModel, slug=payload.branch_slug)

    try:
        Consultation.objects.create(
            patient_name=payload.patient_name,
            patient_phone=payload.patient_phone,
            page_url=build_page_url(request, payload.page_url),
            branch=branch,
            is_ad_agreement=payload.is_ad_agreement,
            is_privacy_agreement=payload.is_privacy_agreement,
        )

        return 201, {"message": "Запись на консультацию создана"}
    except Exception:
        return 400, {"message": "Некорректные данные при отправке"}
