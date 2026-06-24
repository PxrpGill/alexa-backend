from django.db import models


class Branch(models.Model):
    class Meta:
        verbose_name = 'Филиал'
        verbose_name_plural = 'Филиалы'

    def __str__(self):
        return f'Branch {self.pk}'
