from apps.common.models import SingletonModel


class LandyshevayaPediatricConsultationModel(SingletonModel):
    """Детская консультация филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Детская консультация филиала Ландышевая"
        verbose_name_plural = "Детская консультация филиала Ландышевая"

    def __str__(self):
        return "Детская консультация (Ландышевая)"
