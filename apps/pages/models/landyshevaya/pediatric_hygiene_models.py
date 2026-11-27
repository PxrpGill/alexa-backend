from apps.common.models import SingletonModel


class LandyshevayaPediatricHygieneModel(SingletonModel):
    """Детская гигиена филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Детская гигиена филиала Ландышевая"
        verbose_name_plural = "Детская гигиена филиала Ландышевая"

    def __str__(self):
        return "Детская гигиена (Ландышевая)"
