from apps.common.models import SingletonModel


class LandyshevayaAdultPeriodontologyModel(SingletonModel):
    """Взрослая пародонтология филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Взрослая пародонтология филиала Ландышевая"
        verbose_name_plural = "Взрослая пародонтология филиала Ландышевая"

    def __str__(self):
        return "Взрослая пародонтология (Ландышевая)"
