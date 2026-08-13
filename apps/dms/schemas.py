from typing import Optional
from ninja import Schema


class DMSCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    page_url: Optional[str] = None
    branch_slug: str
    is_ad_agreement: Optional[bool] = None
    is_privacy_agreement: Optional[bool] = None
