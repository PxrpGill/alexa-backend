from django.contrib import admin
from .models import BranchModel, PagesModel


@admin.register(PagesModel)
class PagesAdmin(admin.ModelAdmin):
    list_display = ["id", "slug", "name"]
    search_fields = ['slug', 'name']
    readonly_fields = ['id']

@admin.register(BranchModel)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["id", "slug", "name"]
    search_fields = ['slug', 'name']
    readonly_fields = ['id']
