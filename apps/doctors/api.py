from ninja import Router
from django.shortcuts import get_object_or_404
from .models import Doctor
from .schemas import DoctorSchema

router = Router(tags=['Врачи'])


@router.get('/', response=list[DoctorSchema])
def list_doctors(request):
    """Список активных врачей."""
    return Doctor.objects.filter(is_active=True).prefetch_related('specializations')


@router.get('/{doctor_id}/', response=DoctorSchema)
def get_doctor(request, doctor_id: int):
    """Информация о враче по ID. 404 если врач неактивен."""
    return get_object_or_404(Doctor, id=doctor_id, is_active=True)