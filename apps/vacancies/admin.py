from django.contrib import admin

from .models import (
    Application,
    Vacancy,
    VacancyBadge,
    VacancyBenefit,
    VacancyBenefitImage,
    VacancyCategory,
    VacancyRequirement,
    VacancyResponsibility,
)


@admin.register(VacancyCategory)
class VacancyCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "sort_order"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["sort_order", "id"]


class VacancyBadgeInline(admin.TabularInline):
    model = VacancyBadge
    extra = 0


class VacancyBenefitInline(admin.TabularInline):
    model = VacancyBenefit
    extra = 0


class VacancyBenefitImageInline(admin.TabularInline):
    model = VacancyBenefitImage
    extra = 0


class VacancyRequirementInline(admin.TabularInline):
    model = VacancyRequirement
    extra = 0


class VacancyResponsibilityInline(admin.TabularInline):
    model = VacancyResponsibility
    extra = 0


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "branch",
        "is_published",
        "sort_order",
        "created_at",
    ]
    list_editable = ["is_published", "sort_order"]
    list_filter = ["is_published", "category", "branch"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "category",
                    "branch",
                    "is_published",
                    "sort_order",
                )
            },
        ),
        (
            "Заголовки секций",
            {
                "fields": (
                    "requirements_title",
                    "partial_requirements_title",
                    "responsibilities_title",
                )
            },
        ),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [
        VacancyBadgeInline,
        VacancyBenefitInline,
        VacancyBenefitImageInline,
        VacancyRequirementInline,
        VacancyResponsibilityInline,
    ]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["created_at", "vacancy", "name", "phone", "status"]
    list_editable = ["status"]
    list_filter = ["status", "vacancy", "created_at"]
    search_fields = ["name", "phone"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    readonly_fields = [
        "created_at",
        "vacancy",
        "name",
        "phone",
        "resume",
        "privacy_policy_accepted",
        "privacy_policy_accepted_at",
    ]
