from ninja import Schema


class AppointmentCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_name: str


class AppointmentResponseSchema(Schema):
    id: int
    patient_name: str
    status: str
