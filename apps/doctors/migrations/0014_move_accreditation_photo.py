"""Переносит единственное изображение аккредитации в DoctorAccreditationFile."""

from django.db import migrations


def move_photos(apps, schema_editor):
    DoctorAccreditation = apps.get_model("doctors", "DoctorAccreditation")
    DoctorAccreditationFile = apps.get_model("doctors", "DoctorAccreditationFile")

    DoctorAccreditationFile.objects.bulk_create(
        [
            DoctorAccreditationFile(
                accreditation_id=accreditation.pk,
                image=accreditation.photo.name,
                sort_order=0,
            )
            for accreditation in DoctorAccreditation.objects.exclude(photo="").exclude(
                photo__isnull=True
            )
        ]
    )


def restore_photos(apps, schema_editor):
    DoctorAccreditation = apps.get_model("doctors", "DoctorAccreditation")
    DoctorAccreditationFile = apps.get_model("doctors", "DoctorAccreditationFile")

    for accreditation in DoctorAccreditation.objects.all():
        first = (
            DoctorAccreditationFile.objects.filter(accreditation_id=accreditation.pk)
            .order_by("sort_order", "id")
            .first()
        )
        if first:
            accreditation.photo = first.image.name
            accreditation.save(update_fields=["photo"])


class Migration(migrations.Migration):

    dependencies = [
        ("doctors", "0013_accreditation_files"),
    ]

    operations = [
        migrations.RunPython(move_photos, restore_photos),
        migrations.RemoveField(
            model_name="doctoraccreditation",
            name="photo",
        ),
    ]
