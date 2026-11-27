from apps.common.models import SingletonModel


class LandyshevayaAdultTreatmentDuringSleepModel(SingletonModel):
    """Взрослое лечение во сне филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослое лечение во сне филиала Ландышевая"
        verbose_name_plural = "Взрослое лечение во сне филиала Ландышевая"

    def __str__(self):
        return "Взрослое лечение во сне (Ландышевая)"
