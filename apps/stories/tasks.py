import logging

from celery import shared_task

from .media import process_story_image, transcode_story_video

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def process_story_preview_task(pk):
    """webp/avif и мобильная копия обложки группы."""
    from .models import StoryGroup

    group = StoryGroup.objects.filter(pk=pk).first()
    if group and group.preview:
        process_story_image(group.preview)


@shared_task
def process_story_item_task(pk):
    """Обработать медиа кадра и перевести его в READY (или ERROR).

    Без автоповторов: ошибка ffmpeg на битом файле детерминирована, повтор
    только занял бы worker. Кадр со статусом ERROR перезапускается действием
    в админке.
    """
    from .models import StoryItem, touch_group

    item = StoryItem.objects.filter(pk=pk).first()
    if item is None:
        return

    # Фильтр по текущим файлам: если за время обработки медиа заменили,
    # результат устарел и не должен перетереть статус новой загрузки.
    current = StoryItem.objects.filter(
        pk=pk, type=item.type, image=item.image.name, video=item.video.name,
    )
    current.update(processing_status=StoryItem.ProcessingStatus.PROCESSING)

    try:
        if item.type == StoryItem.Type.IMAGE:
            process_story_image(item.image)
            result = {}
        else:
            result = transcode_story_video(item.video)
    except Exception as exc:
        logger.exception('Не удалось обработать медиа кадра сторис (pk=%s)', pk)
        current.update(
            processing_status=StoryItem.ProcessingStatus.ERROR,
            processing_error=str(exc)[:1000],
        )
        return

    if current.update(processing_status=StoryItem.ProcessingStatus.READY, **result):
        touch_group(item.group_id)
