from typing import Optional

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Form, Router, UploadedFile

from apps.common.schemas import ErrorResponseMessageSchema, SuccessResponseMessageSchema
from apps.common.throttling import throttle

from .models import Application, Vacancy, VacancyCategory
from .schemas import (
    ApplicationCreateSchema,
    ApplicationErrorSchema,
    VacanciesListResponseSchema,
    VacancyDetailSchema,
)
from .validators import validate_application

router = Router(tags=["Вакансии"])

RESUME_THROTTLE_LIMIT = 10
RESUME_THROTTLE_WINDOW = 60


@router.get("", response=VacanciesListResponseSchema)
def list_vacancies(request, category: str | None = None):
    """Список опубликованных вакансий. Фильтрация по категории: ?category=<slug>."""
    categories = list(VacancyCategory.objects.filter(is_active=True))
    vacancies = Vacancy.objects.filter(
        is_published=True, category__is_active=True
    ).select_related("category", "branch")
    if category:
        vacancies = vacancies.filter(category__slug=category)
    return {
        "categories": categories,
        "results": list(vacancies),
    }


def _create_application(request: HttpRequest, payload, resume, vacancy):
    errors = validate_application(payload, resume)
    if errors:
        return 400, errors

    Application.objects.create(
        vacancy=vacancy,
        name=payload.name.strip(),
        phone=payload.phone,
        resume=resume,
        privacy_policy_accepted=True,
        privacy_policy_accepted_at=timezone.now(),
    )
    return 201, {"message": "Отклик отправлен"}


@router.post(
    "/apply",
    response={
        201: SuccessResponseMessageSchema,
        400: ApplicationErrorSchema,
        429: ErrorResponseMessageSchema,
    },
    exclude_none=True,
)
@throttle(
    RESUME_THROTTLE_LIMIT,
    RESUME_THROTTLE_WINDOW,
    message="Слишком много откликов. Попробуйте позже.",
)
def general_apply(
    request,
    payload: ApplicationCreateSchema = Form(...),
    resume: Optional[UploadedFile] = File(None),
):
    """Отклик без привязки к конкретной вакансии (multipart/form-data)."""
    return _create_application(request, payload, resume, None)


@router.post(
    "/{slug}/apply",
    response={
        201: SuccessResponseMessageSchema,
        400: ApplicationErrorSchema,
        429: ErrorResponseMessageSchema,
    },
    exclude_none=True,
)
@throttle(
    RESUME_THROTTLE_LIMIT,
    RESUME_THROTTLE_WINDOW,
    message="Слишком много откликов. Попробуйте позже.",
)
def apply_to_vacancy(
    request,
    slug: str,
    payload: ApplicationCreateSchema = Form(...),
    resume: Optional[UploadedFile] = File(None),
):
    """Отклик на конкретную вакансию (multipart/form-data)."""
    vacancy = get_object_or_404(Vacancy, slug=slug, is_published=True)
    return _create_application(request, payload, resume, vacancy)


@router.get("/{slug}", response=VacancyDetailSchema)
def get_vacancy(request, slug: str):
    """Детальная информация о вакансии по slug. 404 если вакансия не опубликована."""
    return get_object_or_404(
        Vacancy.objects.select_related("category", "branch").prefetch_related(
            "badges", "benefits", "benefit_images", "requirements", "responsibilities"
        ),
        slug=slug,
        is_published=True,
    )
