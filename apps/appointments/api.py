from ninja import Router
from django.shortcuts import get_object_or_404
from .models import Appointment
from .schemas import AppointmentCreateSchema, AppointmentResponseSchema
from apps.branches.models import Branch

router = Router(tags=['Appointments'])


@router.post('/', response={201: AppointmentResponseSchema})
def create_appointment(request, payload: AppointmentCreateSchema):
    branch = get_object_or_404(Branch, id=payload.branch_id, is_active=True)
    appt = Appointment.objects.create(
        patient_name=payload.patient_name,
        patient_phone=payload.patient_phone,
        branch=branch,
        doctor_id=payload.doctor_id,
        service_id=payload.service_id,
        comment=payload.comment,
    )
    return 201, appt
