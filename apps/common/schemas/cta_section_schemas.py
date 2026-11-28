from ninja import Schema
from typing import Optional


class CtaSectionSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
