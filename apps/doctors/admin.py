from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline
from .models import Doctor, AboutDoctorTab, AboutDoctorTabContent, DoctorAccreditation


class DoctorAccreditationAdminForm(StackedInline):
    model = DoctorAccreditation
    extra = 0


class AboutDoctorTabContentAdminForm(StackedInline):
    model = AboutDoctorTabContent
    extra = 0


class AboutDoctorTabAdminForm(StackedInline):
    model = AboutDoctorTab
    extra = 0
    readonly_fields = ("slug",)


@admin.register(Doctor)
class DoctorAdmin(ModelAdmin):
    inlines = [
        AboutDoctorTabAdminForm,
        AboutDoctorTabContentAdminForm,
        DoctorAccreditationAdminForm,
    ]
