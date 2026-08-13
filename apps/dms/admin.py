from django.contrib import admin
from .models import DMS


@admin.register(DMS)
class DMSAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_phone', 'branch', 'status', 'page_url', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'branch']
    search_fields = ['patient_name', 'patient_phone']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
