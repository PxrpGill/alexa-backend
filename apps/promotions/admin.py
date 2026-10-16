from django.contrib import admin
from django.forms.formsets import DELETION_FIELD_NAME, ORDERING_FIELD_NAME
from django.forms.models import BaseInlineFormSet

from apps.common.admin import make_image_preview

from .content import has_content
from .models import (
    Promotion,
    PromotionRequests,
    PromotionRequestFormModel
)

# CKEditor пишет в пустое поле разметку вида "<p><br></p>" или "<p>&nbsp;</p>",
# из-за чего пустая строка инлайна считается "изменённой" и Django сохраняет её.


class SkipEmptyInlineFormSet(BaseInlineFormSet):
    """Не сохранять новые строки инлайна, в которых все поля пустые."""

    def save_new_objects(self, commit=True):
        self.new_objects = []
        for form in self.extra_forms:
            if not form.has_changed():
                continue
            if self.can_delete and self._should_delete_form(form):
                continue
            if not self._has_content(form):
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
            if not commit:
                self.saved_forms.append(form)
        return self.new_objects

    def _has_content(self, form):
        cleaned = form.cleaned_data or {}
        for field_name, value in cleaned.items():
            if field_name in (DELETION_FIELD_NAME, self.fk.name, ORDERING_FIELD_NAME):
                continue
            if has_content(value):
                return True
        return False


class PromotionRequestFormAdminModel(admin.StackedInline):
    model = PromotionRequestFormModel
    extra = 1

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ["banner_preview", "title", "starts_at", "ends_at", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["is_active"]
    search_fields = ["title"]
    readonly_fields = ["banner_preview", "banner_mobile_preview"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "description", "is_active")}),
        (
            "Баннеры",
            {
                "fields": (
                    ("banner", "banner_preview"),
                    ("banner_mobile", "banner_mobile_preview"),
                )
            },
        ),
        (
            "Внутренняя страница",
            {"fields": ("detail_title", "detail_description", "detail_content")},
        ),
        ("Сроки", {"fields": ("starts_at", "ends_at")}),
    )
    inlines = [PromotionRequestFormAdminModel]

    banner_preview = make_image_preview("banner", label="Баннер")
    banner_mobile_preview = make_image_preview("banner_mobile", label="Баннер (моб.)")


@admin.register(PromotionRequests)
class PromotionRequestAdmin(admin.ModelAdmin):
    list_display = [
        "patient_name",
        "patient_phone",
        "promotion",
        "status",
        "is_ad_agreement",
        "is_privacy_agreement",
    ]
    search_fields = ["patient_name", "patient_phone"]
