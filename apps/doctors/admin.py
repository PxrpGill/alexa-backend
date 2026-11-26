from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from .models import (
    Doctor,
    AboutDoctorInformation,
    AboutDoctorTab,
    AboutDoctorTabContent,
)


@admin.register(Doctor)
class DoctorAdmin(NestedModelAdmin):
    inlines = [AboutDoctorTabContent]

    list_display = ["full_name", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["full_name"]
    list_filter = ["is_active"]
