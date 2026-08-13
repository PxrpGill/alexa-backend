from typing import Optional
from ninja import Schema


class ConsultationCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_slug: str
    page_url: Optional[str] = None
    is_ad_agreement: Optional[bool] = None
    is_privacy_agreement: Optional[bool] = None
