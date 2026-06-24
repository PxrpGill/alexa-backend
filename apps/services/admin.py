from django.contrib import admin
from .models import ServiceCategory, Service, BranchService


class BranchServiceInline(admin.TabularInline):
    model = BranchService
    extra = 1

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(branch=branch)
        return qs.none()


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_editable = ['is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BranchServiceInline]
