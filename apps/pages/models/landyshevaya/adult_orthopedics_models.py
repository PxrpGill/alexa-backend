from apps.common.models import SingletonModel


class LandyshevayaAdultOrthopedicsModel(SingletonModel):
    """Взрослая ортопедия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая ортопедия филиала Ландышевая"
        verbose_name_plural = "Взрослая ортопедия филиала Ландышевая"

    def __str__(self):
        return "Взрослая ортопедия (Ландышевая)"
