from apps.common.models import SingletonModel


class LandyshevayaAdultSurgeryAndImplantationModel(SingletonModel):
    """Взрослая хирургия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая хирургия филиала Ландышевая"
        verbose_name_plural = "Взрослая хирургия филиала Ландышевая"

    def __str__(self):
        return "Взрослая хирургия (Ландышевая)"
