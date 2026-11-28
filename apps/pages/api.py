from ninja import Router
from django.shortcuts import get_object_or_404

from .models import LandyshevayaMainPageModel

from apps.pages.schemas.landyshevaya.landyshevaya_main_page_schemas import (
    LandyshevayaMainPageSchema,
)

router = Router(tags=["Контент страниц"])


@router.get(
    "/landyshevaya/main", response=LandyshevayaMainPageSchema, exclude_none=True
)
def get_main_page_content(request):
    return get_object_or_404(
        LandyshevayaMainPageModel.objects.prefetch_related(
            "hero_slides",
            "curatorssectionmodel",
            "ctasectionmodel",
            "ourworksectionmodel__ourworkimagegallerymodel_set",
            "titledescriptionsliderssectionmodel__titledescriptionslidemodel_set"
            "__titledescriptionslidegallerymodel_set",
            "faqsectionmodel__faqfactoidsmodel_set",
        ),
        pk=1,
    )
