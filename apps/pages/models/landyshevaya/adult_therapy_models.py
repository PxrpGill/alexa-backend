from apps.common.models import SingletonModel


class LandyshevayaAdultTherapyModel(SingletonModel):
    """Взрослая терапия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая терапия филиала Ландышевая"
        verbose_name_plural = "Взрослая терапия филиала Ландышевая"

    def __str__(self):
        return "Взрослая терапия (Ландышевая)"
