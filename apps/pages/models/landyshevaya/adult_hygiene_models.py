from apps.common.models import SingletonModel


class LandyshevayaAdultHygieneModel(SingletonModel):
    """Взрослая гигиена филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая гигиена филиала Ландышевая"
        verbose_name_plural = "Взрослая гигиена филиала Ландышевая"

    def __str__(self):
        return "Взрослая гигиена (Ландышевая)"
