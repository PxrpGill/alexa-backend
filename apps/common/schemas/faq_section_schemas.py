from typing import Optional
from ninja import Schema


class FaqFactoidSchema(Schema):
    question: str
    answer: str


class FaqSectionSchema(Schema):
    title: Optional[str]
    cards: Optional[list[FaqFactoidSchema]]
