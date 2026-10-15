from django.contrib import admin
from .models import (
    Promotion,
    PromotionCondition,
    PromotionRequests,
    WhatPromotionInclude,
    WhyItMatters,
    TargetAudience,
)


class PromotionConditionInline(admin.TabularInline):
    model = PromotionCondition
    extra = 1
    fields = ["icon", "title", "description", "sort_order"]


class PromotionWhatInclude(admin.TabularInline):
    model = WhatPromotionInclude
    extra = 1
    fields = ["title", "description"]


class PromotionWhyItMatters(admin.TabularInline):
    model = WhyItMatters
    extra = 1
    fields = ["title", "description"]


class PromotionTargetAudience(admin.TabularInline):
    model = TargetAudience
    extra = 1
    fields = ["title", "description"]


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    inlines = [
        PromotionConditionInline,
        PromotionWhatInclude,
        PromotionWhyItMatters,
        PromotionTargetAudience,
    ]
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
