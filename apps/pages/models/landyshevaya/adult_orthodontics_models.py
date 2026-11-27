from apps.common.models import SingletonModel


class LandyshevayaAdultOrthodonticsModel(SingletonModel):
    """Взрослая ортодонтия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая ортодонтия филиала Ландышевая"
        verbose_name_plural = "Взрослая ортодонтия филиала Ландышевая"

    def __str__(self):
        return "Взрослая ортодонтия (Ландышевая)"
