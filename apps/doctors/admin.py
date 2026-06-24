from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Doctor, Specialization, DoctorBranch


class DoctorBranchInline(admin.TabularInline):
    model = DoctorBranch
    extra = 1


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Doctor)
class DoctorAdmin(BranchFilterMixin, admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'patronymic', 'is_active']
    list_editable = ['is_active']
    search_fields = ['last_name', 'first_name', 'patronymic']
    list_filter = ['is_active', 'specializations']
    filter_horizontal = ['specializations']
    inlines = [DoctorBranchInline]
    branch_filter_field = 'doctorbranch__branch'
