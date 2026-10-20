from adminsortable2.admin import SortableAdminMixin, SortableStackedInline
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html

from .models import StoryGroup, StoryItem, enqueue_media_processing

_STATUS_COLORS = {
    StoryItem.ProcessingStatus.PENDING: "#6c757d",
    StoryItem.ProcessingStatus.PROCESSING: "#007bff",
    StoryItem.ProcessingStatus.READY: "#28a745",
    StoryItem.ProcessingStatus.ERROR: "#dc3545",
}


class StoryItemInline(SortableStackedInline):
    model = StoryItem
    extra = 0
    fields = [
        "type",
        "image",
        "video",
        "duration",
        "media_preview",
        "processing_status_display",
    ]
    readonly_fields = ["media_preview", "processing_status_display"]

    @admin.display(description="Превью")
    def media_preview(self, obj):
        if obj.type == StoryItem.Type.IMAGE and obj.image:
            return format_html(
                '<img src="{}" style="max-height: 240px; border-radius: 6px;">',
                obj.image.url,
            )
        if obj.type == StoryItem.Type.VIDEO and obj.video:
            src = obj.video_mobile or obj.video
            poster = obj.video_poster.url if obj.video_poster else ""
            return format_html(
                '<video src="{}" poster="{}" controls preload="metadata" '
                'style="max-height: 240px; border-radius: 6px;"></video>',
                src.url,
                poster,
            )
        return "—"

    @admin.display(description="Обработка")
    def processing_status_display(self, obj):
        if obj.pk is None:
            return "—"
        label = format_html(
            '<b style="color: {}">{}</b>',
            _STATUS_COLORS[obj.processing_status],
            obj.get_processing_status_display(),
        )
        if obj.processing_status == StoryItem.ProcessingStatus.ERROR:
            return format_html(
                "{}<br><small>{}</small>", label, obj.processing_error[:300]
            )
        return label


@admin.register(StoryGroup)
class StoryGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        "preview_thumbnail",
        "__str__",
        "is_published",
        "publish_window",
        "items_count",
    ]
    list_editable = ["is_published"]
    list_filter = ["is_published"]
    fields = ["title", "preview", "is_published", "publish_from", "publish_to"]
    inlines = [StoryItemInline]
    actions = ["reprocess_media"]

    def get_queryset(self, request):
        # Meta.ordering не применяется к запросам с GROUP BY — задаём явно.
        return (
            super()
            .get_queryset(request)
            .annotate(items_total=Count("items"))
            .order_by("order", "id")
        )

    @admin.display(description="Обложка")
    def preview_thumbnail(self, obj):
        if not obj.preview:
            return "—"
        return format_html(
            '<img src="{}" style="width: 48px; height: 48px; object-fit: cover; '
            'border-radius: 50%;">',
            obj.preview.url,
        )

    @admin.display(description="Окно показа")
    def publish_window(self, obj):
        if not obj.publish_from and not obj.publish_to:
            return "без ограничения"
        fmt = "%d.%m.%Y %H:%M"
        start = (
            timezone.localtime(obj.publish_from).strftime(fmt)
            if obj.publish_from
            else "…"
        )
        end = (
            timezone.localtime(obj.publish_to).strftime(fmt)
            if obj.publish_to
            else "…"
        )
        return f"{start} — {end}"

    @admin.display(description="Кадров", ordering="items_total")
    def items_count(self, obj):
        return obj.items_total

    @admin.action(description="Перезапустить обработку незавершённых кадров")
    def reprocess_media(self, request, queryset):
        items = StoryItem.objects.filter(group__in=queryset).exclude(
            processing_status=StoryItem.ProcessingStatus.READY
        )
        pks = list(items.values_list("pk", flat=True))
        items.update(
            processing_status=StoryItem.ProcessingStatus.PENDING, processing_error=""
        )
        for pk in pks:
            transaction.on_commit(lambda pk=pk: enqueue_media_processing("item", pk))
        self.message_user(
            request, f"Кадров поставлено в обработку: {len(pks)}", messages.SUCCESS
        )
