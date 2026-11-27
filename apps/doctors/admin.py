from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline
from .models import Doctor, AboutDoctorTab, AboutDoctorTabContent, DoctorAccreditation


class DoctorAccreditationAdminForm(StackedInline):
    model = DoctorAccreditation
    extra = 0


class AboutDoctorTabContentAdminForm(StackedInline):
    model = AboutDoctorTabContent
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Раздел создаётся на враче и принадлежит только ему — в списке
        # показываем разделы текущего сотрудника (у нового врача их ещё нет).
        tabs = (
            AboutDoctorTab.objects.filter(doctor=obj)
            if obj
            else AboutDoctorTab.objects.none()
        )
        formset.form.base_fields["tab"].queryset = tabs
        return formset


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
