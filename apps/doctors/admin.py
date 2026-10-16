import nested_admin
from django.contrib import admin

from apps.common.admin import make_image_preview

from .models import (
    Doctor,
    DoctorAccreditation,
    DoctorAccreditationFile,
    DoctorBioInformation,
    DoctorJobResults,
    DoctorReferral,
)


class DoctorAccreditationFileInline(nested_admin.NestedTabularInline):
    model = DoctorAccreditationFile
    extra = 0
    fields = ["image", "image_preview", "alt", "sort_order"]
    readonly_fields = ["image_preview"]

    image_preview = make_image_preview("image")


class DoctorAccreditationAdmin(nested_admin.NestedStackedInline):
    model = DoctorAccreditation
    extra = 0
    fields = ["title"]
    inlines = [DoctorAccreditationFileInline]


class DoctorBioInformationAdmin(nested_admin.NestedStackedInline):
    model = DoctorBioInformation
    extra = 0
    fields = ["title", "description"]


class DoctorJobResultsAdmin(nested_admin.NestedStackedInline):
    model = DoctorJobResults
    extra = 0
    fields = [
        "title",
        "description",
        ("photo_before", "photo_before_preview"),
        ("photo_before_mobile", "photo_before_mobile_preview"),
        ("photo_after", "photo_after_preview"),
        ("photo_after_mobile", "photo_after_mobile_preview"),
    ]
    readonly_fields = [
        "photo_before_preview",
        "photo_before_mobile_preview",
        "photo_after_preview",
        "photo_after_mobile_preview",
    ]

    photo_before_preview = make_image_preview("photo_before", label="Превью «до»")
    photo_before_mobile_preview = make_image_preview(
        "photo_before_mobile", label="Превью «до» (моб.)"
    )
    photo_after_preview = make_image_preview("photo_after", label="Превью «после»")
    photo_after_mobile_preview = make_image_preview(
        "photo_after_mobile", label="Превью «после» (моб.)"
    )


@admin.register(Doctor)
class DoctorAdmin(nested_admin.NestedModelAdmin):
    list_display = [
        "photo_preview",
        "last_name",
        "first_name",
        "patronymic",
        "is_active",
    ]
    list_editable = ["is_active"]
    search_fields = ["last_name", "first_name", "patronymic"]
    list_filter = [
        "is_active",
    ]
    filter_horizontal = ["job_referral"]
    readonly_fields = ["photo_preview", "photo_mobile_preview"]
    fieldsets = (
        (None, {"fields": ("last_name", "first_name", "patronymic", "is_active")}),
        (
            "Фото",
            {
                "fields": (
                    ("photo", "photo_preview"),
                    ("photo_mobile", "photo_mobile_preview"),
                )
            },
        ),
        ("Направления", {"fields": ("job_referral",)}),
    )
    inlines = [
        DoctorBioInformationAdmin,
        DoctorJobResultsAdmin,
        DoctorAccreditationAdmin,
    ]

    photo_preview = make_image_preview("photo", label="Фото")
    photo_mobile_preview = make_image_preview("photo_mobile", label="Фото (моб.)")


@admin.register(DoctorReferral)
class ReferralsDirectory(admin.ModelAdmin):
    list_display = ["title"]
    search_fields = ["title"]
