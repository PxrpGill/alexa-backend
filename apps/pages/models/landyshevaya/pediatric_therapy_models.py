from apps.common.models import SingletonModel


class LandyshevayaPediatricTherapyModel(SingletonModel):
    """Детская терапия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Детская терапия филиала Ландышевая"
        verbose_name_plural = "Детская терапия филиала Ландышевая"

    def __str__(self):
        return "Детская терапия (Ландышевая)"
