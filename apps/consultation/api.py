from ninja import Router
from .models import Consultation
from .schemas import ConsultationCreateSchema
from ..common.schemas import SuccessResponseMessageSchema, ErrorResponseMessageSchema

router = Router(tags=["Запись на приём"])


@router.post(
    "/", response={201: SuccessResponseMessageSchema, 400: ErrorResponseMessageSchema}
)
def create_appointment(request, payload: ConsultationCreateSchema):
    """Создать запись ДМС. Возвращает созданную запись (201)."""

    try:
        Consultation.objects.create(
            patient_name=payload.patient_name,
            patient_phone=payload.patient_phone,
            branch_name=payload.branch_name,
        )

        return 201, {"message": "Запись дмс создана"}
    except Exception:
        return 400, {"message": "Некорректные данные при отправке"}
