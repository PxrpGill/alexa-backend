from django.contrib import admin
from .models import BranchModel


@admin.register(BranchModel)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["id", "slug", "name"]
    search_fields = ['slug', 'name']
    readonly_fields = ['id']
