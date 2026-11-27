from apps.common.models import SingletonModel


class LandyshevayaAdultGnathologyModel(SingletonModel):
    """Взрослая гнатология филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая гнатология филиала Ландышевая"
        verbose_name_plural = "Взрослая гнатология филиала Ландышевая"

    def __str__(self):
        return "Взрослая гнатология (Ландышевая)"
