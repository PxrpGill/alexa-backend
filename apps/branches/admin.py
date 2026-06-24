from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Branch


@admin.register(Branch)
class BranchAdmin(BranchFilterMixin, admin.ModelAdmin):
    list_display = ['name', 'address', 'phone', 'email', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'address']
    list_filter = ['is_active']

    def get_queryset(self, request):
        qs = admin.ModelAdmin.get_queryset(self, request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(id=branch.id)
        return qs.none()
