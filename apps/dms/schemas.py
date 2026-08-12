from ninja import Schema


class DMSCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_name: str
