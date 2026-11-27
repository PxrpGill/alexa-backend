from apps.common.models import SingletonModel


class LandyshevayaPediatricSurgeryAndImplantationModel(SingletonModel):
    """Детская хирургия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Детская хирургия филиала Ландышевая"
        verbose_name_plural = "Детская хирургия филиала Ландышевая"

    def __str__(self):
        return "Детская хирургия (Ландышевая)"
