from ninja import Schema
from typing import Optional


class SiteButtonSchema(Schema):
    button_title: Optional[str] = None
    button_href: Optional[str] = None
    button_target: Optional[str] = None
    is_open_feedback_modal: bool = False
