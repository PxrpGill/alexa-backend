from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'branch'
    list_display = ['patient_name', 'patient_phone', 'branch', 'doctor', 'service', 'status', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'branch']
    search_fields = ['patient_name', 'patient_phone']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
