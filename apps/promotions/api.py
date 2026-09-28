from ninja import Router
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Promotion, PromotionRequests
from .schemas import PromotionSchema, PromotionDetailSchema, PromotionRequestSchema
from ..common.throttling import throttle_lead_form
from ..common.schemas import SuccessResponseMessageSchema, ErrorResponseMessageSchema

router = Router(tags=["Акции"])


def active_promotions():
    """Акции, активные на сегодняшнюю дату (ends_at=None — бессрочная)."""
    today = timezone.localdate()
    return Promotion.objects.filter(
        is_active=True,
        starts_at__lte=today,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=today))


@router.get("", response=list[PromotionSchema])
def list_promotions(request):
    """Активные акции на сегодняшнюю дату."""
    return active_promotions()


@router.get("/{slug}", response=PromotionDetailSchema)
def get_promotion(request, slug: str):
    """Внутренняя страница акции: hero, подробное описание и условия."""
    return get_object_or_404(
        active_promotions().prefetch_related("conditions"), slug=slug
    )


@router.post(
    "/request",
    response={
        201: SuccessResponseMessageSchema,
        400: ErrorResponseMessageSchema,
        429: ErrorResponseMessageSchema,
    },
)
@throttle_lead_form
def request_to_promotion(request, payload: PromotionRequestSchema):
    """Создать запись на Акцию."""

    if not payload.is_privacy_agreement:
        return 400, {
            "message": "Невозможно создать заявку без согласия с политикой конфиденциальности"
        }

    promotion = get_object_or_404(Promotion, slug=payload.slug)

    try:
        PromotionRequests.objects.create(
            patient_name=payload.patient_name,
            patient_phone=payload.patient_phone,
            promotion=promotion,
            is_ad_agreement=payload.is_ad_agreement,
            is_privacy_agreement=payload.is_privacy_agreement,
        )

        return 201, {"message": "Запись на акцию успешно создана"}
    except Exception:
        return 400, {"message": "Некорректные данные при отправке"}
