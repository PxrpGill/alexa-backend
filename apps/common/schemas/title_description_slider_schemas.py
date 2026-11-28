from ninja import Schema
from typing import Optional


class TitleDescriptionSliderSchema(Schema):
    title: Optional[str]
    description: Optional[str]


class TitleDescriptionSliderSlidersSchema(Schema):
    title: Optional[str]