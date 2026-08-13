from ninja import Router
from django.shortcuts import get_object_or_404

from apps.branch.models import BranchModel

from .models import Consultation
from .schemas import ConsultationCreateSchema
from ..common.schemas import SuccessResponseMessageSchema, ErrorResponseMessageSchema

router = Router(tags=["Запись на приём"])


@router.post(
    "", response={201: SuccessResponseMessageSchema, 400: ErrorResponseMessageSchema}
)
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
            page_url=(
                request.build_absolute_uri(payload.page_url)
                if payload.page_url
                else "/"
            ),
            branch=branch,
            is_ad_agreement=payload.is_ad_agreement,
            is_privacy_agreement=payload.is_privacy_agreement,
        )

        return 201, {"message": "Запись на консультацию создана"}
    except Exception:
        return 400, {"message": "Некорректные данные при отправке"}
