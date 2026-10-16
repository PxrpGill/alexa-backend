from django.contrib import admin
from .models import (
    Doctor,
    DoctorAccreditation,
    DoctorBioInformation,
    DoctorJobResults,
    DoctorReferral,
)


class DoctorAccreditationAdmin(admin.StackedInline):
    model = DoctorAccreditation
    extra = 1


class DoctorBioInformationAdmin(admin.StackedInline):
    model = DoctorBioInformation
    extra = 1


class DoctorJobResultsAdmin(admin.StackedInline):
    model = DoctorJobResults
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["last_name", "first_name", "patronymic", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["last_name", "first_name", "patronymic"]
    list_filter = [
        "is_active",
    ]
    inlines = [
        DoctorBioInformationAdmin,
        DoctorJobResultsAdmin,
        DoctorAccreditationAdmin,
    ]


@admin.register(DoctorReferral)
class ReferralsDirectory(admin.ModelAdmin):
    list_display = ["title"]