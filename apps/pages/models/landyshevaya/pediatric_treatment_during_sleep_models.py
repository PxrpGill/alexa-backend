from apps.common.models import SingletonModel


class LandyshevayaPediatricTreatmentDuringSleepModel(SingletonModel):
    """Детское лечение во сне филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Детское лечение во сне филиала Ландышевая"
        verbose_name_plural = "Детское лечение во сне филиала Ландышевая"

    def __str__(self):
        return "Детское лечение во сне (Ландышевая)"
