from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from .models import Doctor
from .schemas import DoctorSchema

router = Router(tags=['Врачи'])


def _doctors():
    """Активные врачи с предзагрузкой «О сотруднике» и аккредитаций (иначе N+1)."""
    return Doctor.objects.filter(is_active=True).prefetch_related(
        'doctor_informations__tab_contents',
        'doctor_accreditation',
    )


@router.get('', response=list[DoctorSchema], exclude_none=True)
def list_doctors(request, page_slug: str | None = None):
    """Список активных врачей. `page_slug` фильтрует по странице сайта."""
    doctors = _doctors()

    if page_slug:
        doctors = doctors.filter(pages__slug=page_slug)
        
    return doctors


@router.get('/{doctor_id}', response=DoctorSchema, exclude_none=True)
def get_doctor(request, doctor_id: UUID):
    """Информация о враче по ID. 404 если врач неактивен."""
    return get_object_or_404(_doctors(), pk=doctor_id)
