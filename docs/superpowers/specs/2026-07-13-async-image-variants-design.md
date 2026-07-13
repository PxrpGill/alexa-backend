# Асинхронная генерация webp/avif через Celery + Redis

## Контекст

В [2026-07-13-image-variants-design.md](2026-07-13-image-variants-design.md) реализована
синхронная генерация webp/avif-вариантов при сохранении изображения
(`apps.common.mixins.ImageVariantsMixin.save()` → `apps.common.images.generate_image_variants()`
напрямую внутри `Model.save()`).

Замер на реальных размерах фото показал, что AVIF-кодирование занимает заметное время
(сотни мс — ~1 с на изображение, в 5–15 раз медленнее WebP). Для моделей с несколькими
image-полями за один сабмит (например `BlogPost`: `poster`, `poster_mobile`,
`preview_poster`, `preview_poster_mobile`) это может добавлять 2-4 секунды к сохранению
в admin. Цель этой задачи — вынести генерацию за пределы request-цикла.

## Цель

`ImageVariantsMixin.save()` продолжает сохранять модель мгновенно (без изменений в
скорости самого `save()`), но генерация `.webp`/`.avif` происходит асинхронно в
отдельном Celery worker'е. До завершения задачи API отдаёт `PictureFormatType` с
заполненным только `original` — `webp`/`avif` появляются в ответе, как только
воркер закончит обработку (это уже поддерживается существующей логикой
`build_picture_format()`, которая возвращает `None` для отсутствующих вариантов —
изменений в `apps/common/schemas.py` не требуется).

## 1. Инфраструктура: Celery + Redis

Новая зависимость в `requirements.txt`: `celery==5.4.0`, `redis==5.0.8`.

`config/celery.py` — экземпляр Celery-приложения:

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('alexa')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

`config/__init__.py` — обязательная загрузка приложения при старте Django:

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

`config/settings/base.py` — добавить настройки Celery:

```python
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ALWAYS_EAGER = 'test' in sys.argv
```

`CELERY_TASK_ALWAYS_EAGER = 'test' in sys.argv` — во время `manage.py test` задачи
выполняются синхронно в том же процессе (без реального брокера), поэтому все
существующие `*PictureFormatAPITest` продолжают проходить без изменений: сразу после
`save()` webp/avif уже на месте, как и раньше.

Docker (`docker/dev/docker-compose.yml`, `docker/prod/docker-compose.yml`): новый сервис
`redis` (`redis:7-alpine`) и новый сервис `worker` (тот же образ, что и `web`,
команда `celery -A config worker -l info`), оба получают `CELERY_BROKER_URL` через
env. `web` и `worker` зависят от `redis` (`depends_on`).

`CELERY_BROKER_URL=redis://redis:6379/0` добавляется в `docker/dev/.env.dev`
(не в git — файл в `.gitignore`) и в `docker/prod/.env.prod.example` (шаблон в git).

## 2. Задача генерации (`apps/common/tasks.py`)

```python
from celery import shared_task

from apps.common.images import generate_image_variants


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def generate_image_variants_task(app_label, model_name, pk, field_name):
    from django.apps import apps

    model = apps.get_model(app_label, model_name)
    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return

    field_file = getattr(instance, field_name)
    if field_file:
        generate_image_variants(field_file)
```

Задача принимает только примитивные типы (`app_label`, `model_name`, `pk`, `field_name`),
т.к. Celery сериализует аргументы задачи в JSON — `FieldFile`/модельный инстанс
напрямую передать нельзя. Внутри задачи инстанс перечитывается из БД через
`django.apps.apps.get_model()`. `autoretry_for`/`max_retries=3`/`retry_backoff=True` —
защита от временных сбоев (например, storage недоступен на секунду).

## 3. `ImageVariantsMixin` — enqueue вместо прямого вызова

```python
import logging

from apps.common.tasks import generate_image_variants_task

logger = logging.getLogger(__name__)


class ImageVariantsMixin:
    IMAGE_VARIANT_FIELDS = []

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for field_name in self.IMAGE_VARIANT_FIELDS:
            field_file = getattr(self, field_name)
            if not field_file:
                continue
            try:
                generate_image_variants_task.delay(
                    self._meta.app_label, self.__class__.__name__, self.pk, field_name,
                )
            except Exception:
                logger.exception(
                    'Не удалось поставить в очередь генерацию вариантов изображения '
                    '(%s.%s, pk=%s, field=%s)',
                    self._meta.app_label, self.__class__.__name__, self.pk, field_name,
                )
```

Согласно принятому решению: если брокер недоступен — `save()` всё равно завершается
успешно, ошибка только логируется. `original` доступен сразу, `webp`/`avif` не
появятся, пока брокер не восстановится и модель не будет пересохранена (либо не будет
добавлен ручной способ повторной постановки задачи — вне скоупа этой задачи).

## 4. Тестирование

`apps/common/tests.py`:
- Тест на саму задачу `generate_image_variants_task` — используя уже подключённую
  модель `doctors.Doctor` (из первой итерации), напрямую вызвать таску с
  `(app_label, model_name, pk, field_name)`, убедиться что webp/avif появились в storage.
- Тест устойчивости: замокать `generate_image_variants_task.delay` так, чтобы он
  бросал исключение — убедиться, что `Doctor.objects.create(...)` всё равно успешно
  создаёт объект (не падает).

Существующие 5 классов `*PictureFormatAPITest` (doctors/blog/promotions/services) не
меняются — благодаря `CELERY_TASK_ALWAYS_EAGER` в тестах они продолжают проходить
как раньше.

## 5. Известное ограничение (вне скоупа)

Нет механизма ручного/автоматического повторного запуска генерации для объектов,
сохранённых в момент недоступности брокера (кроме пересохранения объекта админом).
Не добавляется в рамках этой задачи — при необходимости можно добавить management
command вида `generate_missing_image_variants`, который проходит по всем моделям с
`ImageVariantsMixin` и ставит в очередь задачи для полей без готовых webp/avif.
