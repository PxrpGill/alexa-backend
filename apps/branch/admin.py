from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import BranchModel, PagesModel


@admin.register(PagesModel)
class PagesAdmin(ModelAdmin):
    list_display = ["id", "slug", "name"]
    search_fields = ['slug', 'name']
    readonly_fields = ['id']

@admin.register(BranchModel)
class BranchAdmin(ModelAdmin):
    list_display = ["id", "slug", "name"]
    search_fields = ['slug', 'name']
    readonly_fields = ['id']
