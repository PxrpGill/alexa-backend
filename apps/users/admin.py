from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'branch', 'is_active']
    list_filter = ['role', 'branch', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Роль и доступ', {'fields': ('role', 'branch')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Роль и доступ', {'fields': ('role', 'branch')}),
    )
