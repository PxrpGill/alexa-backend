from typing import Optional

from ninja import Schema


class FaqFactoidSchema(Schema):
    question: str
    answer: str


class FaqSectionSchema(Schema):
    title: Optional[str] = None
    cards: Optional[list[FaqFactoidSchema]] = None

    @staticmethod
    def resolve_cards(obj):
        return obj.faqfactoidsmodel_set.order_by("pk")
