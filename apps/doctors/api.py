from ninja import Router
from django.shortcuts import get_object_or_404
from typing import Optional
from .models import Doctor
from .schemas import DoctorSchema

router = Router(tags=['Врачи'])


@router.get('/', response=list[DoctorSchema])
def list_doctors(request, branch_id: Optional[int] = None):
    """Список активных врачей. Опциональный фильтр: ?branch_id=<id>."""
    qs = Doctor.objects.filter(is_active=True).prefetch_related('specializations')
    if branch_id is not None:
        qs = qs.filter(doctorbranch__branch_id=branch_id, doctorbranch__is_active=True)
    return qs.distinct()


@router.get('/{doctor_id}/', response=DoctorSchema)
def get_doctor(request, doctor_id: int):
    """Информация о враче по ID. 404 если врач неактивен."""
    return get_object_or_404(Doctor, id=doctor_id, is_active=True)
