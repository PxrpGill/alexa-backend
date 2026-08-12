from django.contrib import admin
from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['title', 'starts_at', 'ends_at', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['title']