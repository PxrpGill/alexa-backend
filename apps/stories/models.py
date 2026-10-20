import logging
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models, transaction
from django.utils import timezone
from django.utils.deconstruct import deconstructible

from .media import MediaProcessingError, probe_uploaded_duration

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = ['mp4', 'mov', 'webm']
MIN_IMAGE_DURATION_MS = 2000
MAX_IMAGE_DURATION_MS = 30000
PROCESSING_FIELDS = frozenset({
    "processing_status", "processing_error", "video_src", "video_mobile", "video_poster",
})


@deconstructible
class UniqueUploadTo:
    """Случайное имя файла в каталоге, расширение сохраняется.

    Варианты (.webp/.avif, -m копия, -src.mp4…) строятся от имени без
    расширения, а Django при коллизии сверяет только полное имя: photo.png и
    photo.jpg делили бы photo.webp, и второй кадр показывал бы картинку первого.
    """

    def __init__(self, directory):
        self.directory = directory

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        return f"{self.directory}{uuid.uuid4().hex}{ext}"


class StoryGroup(models.Model):
    """Группа сторисов — один кружок в ленте на главной."""

    title = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Название",
        help_text="Подпись под кружком и в шапке просмотрщика, до 30 символов",
    )
    preview = models.ImageField(
        upload_to=UniqueUploadTo("stories/previews/"),
        verbose_name="Обложка",
        help_text="Квадрат, от 300×300",
    )
    order = models.PositiveIntegerField(
        default=0, db_index=True, verbose_name="Порядок"
    )
    is_published = models.BooleanField(default=False, verbose_name="Опубликована")
    publish_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Показывать с",
        help_text="Пусто — без ограничения",
    )
    publish_to = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Показывать до",
        help_text="Пусто — без ограничения",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Группа сторисов"
        verbose_name_plural = "Сторисы"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title or f"Группа сторисов #{self.pk}"

    def clean(self):
        if (
            self.publish_from
            and self.publish_to
            and self.publish_from > self.publish_to
        ):
            raise ValidationError(
                {"publish_to": "Окончание показа раньше начала."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.preview:
            pk = self.pk
            transaction.on_commit(lambda: enqueue_media_processing("preview", pk))


class StoryItem(models.Model):
    """Кадр сторис: картинка или видео."""

    class Type(models.TextChoices):
        IMAGE = "image", "Картинка"
        VIDEO = "video", "Видео"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "В очереди"
        PROCESSING = "processing", "Обрабатывается"
        READY = "ready", "Готово"
        ERROR = "error", "Ошибка"

    group = models.ForeignKey(
        StoryGroup,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Группа",
    )
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.IMAGE,
        verbose_name="Тип",
    )
    image = models.ImageField(
        upload_to=UniqueUploadTo("stories/images/"),
        blank=True,
        verbose_name="Картинка",
        help_text="Вертикальный кадр 9:16, от 1080×1920",
    )
    video = models.FileField(
        upload_to=UniqueUploadTo("stories/videos/"),
        blank=True,
        validators=[FileExtensionValidator(VIDEO_EXTENSIONS)],
        verbose_name="Видео",
        help_text="Вертикальное 9:16, до 60 секунд, mp4/mov/webm, до 100 МБ",
    )
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MIN_IMAGE_DURATION_MS),
            MaxValueValidator(MAX_IMAGE_DURATION_MS),
        ],
        verbose_name="Длительность показа, мс",
        help_text="Только для картинки, 2000–30000. Пусто — 7000",
    )
    order = models.PositiveIntegerField(
        default=0, db_index=True, verbose_name="Порядок"
    )

    # Результат фоновой обработки (apps/stories/tasks.py). Пока статус не READY,
    # кадр в API не отдаётся.
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        editable=False,
        verbose_name="Обработка",
    )
    processing_error = models.TextField(
        blank=True, editable=False, verbose_name="Ошибка обработки"
    )
    video_src = models.FileField(
        max_length=255, blank=True, editable=False, verbose_name="Видео 1080p"
    )
    video_mobile = models.FileField(
        max_length=255, blank=True, editable=False, verbose_name="Видео 720p"
    )
    video_poster = models.FileField(
        max_length=255, blank=True, editable=False, verbose_name="Постер видео"
    )

    class Meta:
        verbose_name = "Кадр"
        verbose_name_plural = "Кадры"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.get_type_display()} #{self.pk}" if self.pk else "Новый кадр"

    def clean(self):
        errors = {}
        if self.type == self.Type.IMAGE:
            if not self.image:
                errors["image"] = "Загрузите картинку."
            if self.video:
                errors["video"] = "У кадра-картинки не должно быть видео."
        elif self.type == self.Type.VIDEO:
            if not self.video:
                errors["video"] = "Загрузите видео."
            if self.image:
                errors["image"] = "У кадра-видео не должно быть картинки."
            if self.duration is not None:
                errors["duration"] = (
                    "Для видео длительность не задаётся — её определяет ролик."
                )
            if self.video and "video" not in errors:
                video_error = self._validate_uploaded_video()
                if video_error:
                    errors["video"] = video_error
        if errors:
            raise ValidationError(errors)

    def _validate_uploaded_video(self):
        # Проверяем только новую загрузку: у сохранённого файла уже проверено.
        if getattr(self.video, "_committed", True):
            return None
        if self.video.size > settings.MAX_STORY_VIDEO_SIZE:
            limit_mb = settings.MAX_STORY_VIDEO_SIZE // (1024 * 1024)
            return f"Видео больше {limit_mb} МБ."
        try:
            seconds = probe_uploaded_duration(self.video.file)
        except MediaProcessingError as exc:
            logger.warning("Не удалось прочитать загруженное видео сторис: %s", exc)
            return "Не удалось прочитать видео: файл повреждён или формат не поддерживается."
        if seconds is not None and seconds > settings.MAX_STORY_VIDEO_SECONDS:
            return f"Видео длиннее {settings.MAX_STORY_VIDEO_SECONDS} секунд."
        return None

    def save(self, *args, **kwargs):
        media_changed = self._media_changed()
        if media_changed:
            self.processing_status = self.ProcessingStatus.PENDING
            self.processing_error = ""
            self.video_src = self.video_mobile = self.video_poster = ""
        elif kwargs.get("update_fields") is None:
            # Поля обработки пишет только задача (через .update()). Экземпляр,
            # загруженный до её завершения, иначе вернул бы в БД старый статус.
            kwargs["update_fields"] = [
                field.name
                for field in self._meta.concrete_fields
                if not field.primary_key and field.name not in PROCESSING_FIELDS
            ]
        super().save(*args, **kwargs)
        touch_group(self.group_id)
        if media_changed:
            pk = self.pk
            transaction.on_commit(lambda: enqueue_media_processing("item", pk))

    def delete(self, *args, **kwargs):
        group_id = self.group_id
        result = super().delete(*args, **kwargs)
        touch_group(group_id)
        return result

    def _media_changed(self):
        if self.pk is None:
            return True
        old = (
            StoryItem.objects.filter(pk=self.pk)
            .values("type", "image", "video")
            .first()
        )
        if old is None:
            return True
        return (
            old["type"] != self.type
            or old["image"] != (self.image.name or "")
            or old["video"] != (self.video.name or "")
        )


def touch_group(group_id):
    """Сдвинуть updated_at группы: фронтенд снова покажет её непросмотренной."""
    StoryGroup.objects.filter(pk=group_id).update(updated_at=timezone.now())


def enqueue_media_processing(kind, pk):
    from .tasks import process_story_item_task, process_story_preview_task

    task = process_story_item_task if kind == "item" else process_story_preview_task
    try:
        task.delay(pk)
    except Exception:
        logger.exception(
            "Не удалось поставить в очередь обработку медиа сторис (%s, pk=%s)",
            kind,
            pk,
        )
