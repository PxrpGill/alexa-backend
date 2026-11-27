from apps.common.models.singleton import SingletonModel


class LandyshevayaAdultConsultationModel(SingletonModel):
    """Взрослая консультация филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая консультация филиала Ландышевая"
        verbose_name_plural = "Взрослая консультация филиала Ландышевая"

    def __str__(self):
        return "Взрослая консультация (Ландышевая)"
