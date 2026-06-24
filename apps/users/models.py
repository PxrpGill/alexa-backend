from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Супер-администратор'
        BRANCH_MANAGER = 'branch_manager', 'Менеджер филиала'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BRANCH_MANAGER,
        verbose_name='Роль',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managers',
        verbose_name='Филиал',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.get_full_name() or self.username
