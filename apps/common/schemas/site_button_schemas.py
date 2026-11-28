from ninja import Schema
from typing import Optional


class SiteButtonSchema(Schema):
    button_title: Optional[str]
    button_href = Optional[str]
    button_target = Optional[str]
    is_open_feedback_modal: bool
