from django.core.exceptions import ValidationError
from django.db import models


class SingletonModel(models.Model):
    """Абстрактная модель страницы, у которой может существовать только одна запись.

    Запись всегда хранится с `pk=1`, а `CheckConstraint` не даёт создать вторую
    на уровне БД (в том числе при гонке двух одновременных запросов).
    Повторное создание через админку или код отдаёт `ValidationError`.
    """

    id = models.PositiveSmallIntegerField(
        primary_key=True,
        editable=False,
        verbose_name="Идентификатор",
    )

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=models.Q(pk=1),
                name="%(app_label)s_%(class)s_single_row",
            ),
        ]

    @classmethod
    def load(cls):
        """Вернуть единственную запись, создав её при первом обращении."""
        instance, _created = cls.objects.get_or_create(pk=1)
        return instance

    def clean(self):
        super().clean()
        if self._state.adding and type(self).objects.exists():
            raise ValidationError(
                "Запись уже существует — её можно только редактировать."
            )

    def save(self, *args, **kwargs):
        if self._state.adding:
            if type(self).objects.exists():
                raise ValidationError(
                    "Запись уже существует — её можно только редактировать."
                )
            self.pk = 1
        return super().save(*args, **kwargs)
