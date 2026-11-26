from django.contrib import admin
from .models import Doctor, AboutDoctorTab, AboutDoctorTabContent, DoctorAccreditation


class DoctorAccreditationAdminForm(admin.StackedInline):
    model = DoctorAccreditation
    extra = 0


class AboutDoctorTabContentAdminForm(admin.StackedInline):
    model = AboutDoctorTabContent
    extra = 0


class AboutDoctorTabAdminForm(admin.StackedInline):
    model = AboutDoctorTab
    extra = 0
    readonly_fields = ("slug",)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    inlines = [
        AboutDoctorTabAdminForm,
        AboutDoctorTabContentAdminForm,
        DoctorAccreditationAdminForm,
    ]
