from apps.common.models import SingletonModel


class LandyshevayaPediatricOrthodonticsModel(SingletonModel):
    """Детская ортодонтия филиала Ландышевая"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Детская ортодонтия филиала Ландышевая"
        verbose_name_plural = "Детская ортодонтия филиала Ландышевая"

    def __str__(self):
        return "Детская ортодонтия (Ландышевая)"
