from ninja import Schema
from typing import Optional


class AppointmentCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_name: str
    page_url: Optional[str] = None
