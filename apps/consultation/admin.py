from django.contrib import admin
from .models import Consultation


@admin.register(Consultation)
class DMSAdmin(admin.ModelAdmin):
    list_display = [
        "patient_name",
        "patient_phone",
        "branch",
        "status",
        "page_url",
        "created_at",
        "is_ad_agreement",
        "is_privacy_agreement",
    ]
    list_editable = ["status"]
    list_filter = ["status", "branch"]
    search_fields = ["patient_name", "patient_phone"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"
