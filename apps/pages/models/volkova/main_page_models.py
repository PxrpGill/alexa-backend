from apps.common.models import SingletonModel


class VolkovaMainPageModel(SingletonModel):
    """Главная страница филиала Волкова (ровно одна запись)"""

    class Meta(SingletonModel.Meta):
        verbose_name = "Главная страница филиала Волкова"
        verbose_name_plural = "Главная страница филиала Волкова"

    def __str__(self):
        return "Главная страница (Волкова)"
