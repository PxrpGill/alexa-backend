from django.contrib import admin
from .models import Promotion, PromotionRequests


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ["title", "starts_at", "ends_at", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["is_active"]
    search_fields = ["title"]


@admin.register(PromotionRequests)
class PromotionRequestAdmin(admin.ModelAdmin):
    list_display = [
        "patient_name",
        "patient_phone",
        "promotion",
        "status",
        "is_ad_agreement",
        "is_privacy_agreement",
    ]
    search_fields = ["patient_name", "patient_phone"]
