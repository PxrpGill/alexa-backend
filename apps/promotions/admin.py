from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'branches'
    list_display = ['title', 'starts_at', 'ends_at', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active', 'branches']
    search_fields = ['title']
    filter_horizontal = ['branches']

    def get_queryset(self, request):
        qs = admin.ModelAdmin.get_queryset(self, request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(branches=branch).distinct()
        return qs.none()
