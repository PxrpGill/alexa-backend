from django.db import migrations, models
from django.db.models import Q
from django.utils.text import slugify
from pytils.translit import slugify as t_slugify

SLUG_BASE_MAX_LENGTH = 200


def backfill_slugs(apps, schema_editor):
    """Заполняет пустые слаги разделов: они уходят на фронтенд как tabKey."""
    AboutDoctorTab = apps.get_model("doctors", "AboutDoctorTab")

    for tab in AboutDoctorTab.objects.filter(Q(slug__isnull=True) | Q(slug="")):
        base = (
            slugify(t_slugify(tab.title or ""))[:SLUG_BASE_MAX_LENGTH]
            or f"section-{tab.pk}"
        )
        slug = base
        counter = 1

        while (
            AboutDoctorTab.objects.filter(doctor_id=tab.doctor_id, slug=slug)
            .exclude(pk=tab.pk)
            .exists()
        ):
            slug = f"{base}-{counter}"
            counter += 1

        AboutDoctorTab.objects.filter(pk=tab.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ("doctors", "0011_alter_aboutdoctortab_slug"),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, migrations.RunPython.noop),
    ]
