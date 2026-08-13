from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_phone', 'branch_name', 'status', 'page_url', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'branch_name']
    search_fields = ['patient_name', 'patient_phone']
    readonly_fields = ['created_at', 'page_url']
    date_hierarchy = 'created_at'
