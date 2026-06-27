from ninja import Schema
from typing import Optional


class AppointmentCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_id: int
    doctor_id: Optional[int] = None
    service_id: Optional[int] = None
    comment: str = ''


class AppointmentResponseSchema(Schema):
    id: int
    patient_name: str
    status: str
