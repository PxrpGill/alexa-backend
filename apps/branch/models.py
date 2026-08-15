import uuid
from django.db import models
from django.utils.text import slugify
from django.db.models import Q
from pytils.translit import slugify as t_slugify


# Create your models here.
class BranchModel(models.Model):
    id = models.UUIDField(
        unique=True,
        primary_key=True,
        verbose_name="Идентификатор филиала",
        default=uuid.uuid4,
        editable=False,
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="Текстовый идентификатор филиала",
        blank=True,
    )
    name = models.CharField(
        max_length=255, unique=True, editable=True, verbose_name="Название филиала"
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(t_slugify(self.name)) or f"branch-{uuid.uuid4().hex[:8]}"
            slug = base
            counter = 1

            while BranchModel.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1

            self.slug = slug

        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Список филиалов"
        verbose_name_plural = "Список филиалов"
