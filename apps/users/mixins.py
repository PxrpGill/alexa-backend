class BranchFilterMixin:
    """
    Mixin for ModelAdmin to restrict branch managers to their own branch.
    Set branch_filter_field to the queryset filter path, e.g. 'branch' or 'doctorbranch__branch'.
    """
    branch_filter_field = 'branch'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(**{self.branch_filter_field: branch})
        return qs.none()
