from ninja import Schema


class ConsultationCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_name: str
