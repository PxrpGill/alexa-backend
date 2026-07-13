# Асинхронная генерация webp/avif (Celery + Redis) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Вынести генерацию `.webp`/`.avif` (из [2026-07-13-image-variants.md](2026-07-13-image-variants.md)) из синхронного `Model.save()` в асинхронную Celery-задачу, backed by Redis, чтобы AVIF-кодирование (сотни мс — ~1с на изображение) не замедляло сохранение в admin.

**Architecture:** `ImageVariantsMixin.save()` вместо прямого вызова `generate_image_variants()` ставит в очередь `apps.common.tasks.generate_image_variants_task.delay(app_label, model_name, pk, field_name)`. Задача перечитывает инстанс из БД и вызывает существующий `generate_image_variants()`. Новые сервисы в docker-compose: `redis` (брокер) и `worker` (тот же образ, что и `web`, команда `celery -A config worker`). В тестах `CELERY_TASK_ALWAYS_EAGER = 'test' in sys.argv` заставляет задачи выполняться синхронно in-process — реальный брокер для тестов не нужен, все существующие `*PictureFormatAPITest` продолжают проходить без изменений.

**Tech Stack:** Celery 5.4.0, redis-py 5.0.8, Redis 7 (docker image `redis:7-alpine`).

## Global Constraints

- Если Redis/worker недоступен в момент `save()` — сохранение модели всё равно должно пройти успешно; ошибка постановки задачи в очередь только логируется (см. Task 3).
- `CELERY_TASK_IGNORE_RESULT = True` — результаты задач не нужны (fire-and-forget), результат-бэкенд не настраивается.
- `CELERY_TASK_ALWAYS_EAGER = 'test' in sys.argv` в `config/settings/base.py` — обязательно для того, чтобы существующие тесты (`apps/doctors/tests.py::DoctorPictureFormatAPITest` и аналогичные в blog/promotions/services) продолжали проходить без изменений.
- Задача принимает только примитивные аргументы (`app_label: str`, `model_name: str`, `pk: int`, `field_name: str`) — `FieldFile`/модельный инстанс через Celery не передаются (не сериализуются).
- Тесты запускаются через `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test <label> -v 2 --keepdb`.

---

### Task 1: Инфраструктура Celery + Redis

**Files:**
- Modify: `requirements.txt`
- Create: `config/celery.py`
- Modify: `config/__init__.py`
- Modify: `config/settings/base.py`
- Modify: `docker/dev/docker-compose.yml`
- Modify: `docker/prod/docker-compose.yml`
- Modify: `docker/dev/.env.dev` (не в git)
- Modify: `docker/prod/.env.prod.example`

**Interfaces:**
- Produces: `config.celery.app` — экземпляр `celery.Celery`, обнаруживаемый командой `celery -A config worker`.
- Produces: настройка `CELERY_BROKER_URL` (из env, дефолт `redis://localhost:6379/0`), `CELERY_TASK_IGNORE_RESULT=True`, `CELERY_TASK_ALWAYS_EAGER` (см. Global Constraints), `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=True`.

- [ ] **Step 1: Добавить зависимости**

`requirements.txt` — добавить в конец файла:

```
celery==5.4.0
redis==5.0.8
```

- [ ] **Step 2: Создать `config/celery.py`**

```python
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('alexa')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

- [ ] **Step 3: Подключить Celery-приложение при старте Django**

`config/__init__.py` (сейчас пустой файл) — записать:

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

- [ ] **Step 4: Добавить настройки Celery в `config/settings/base.py`**

В начало файла (строка 1) добавить импорт `sys`:

```python
import sys
from pathlib import Path
from decouple import config
```

После блока `CORS_ALLOWED_ORIGINS = config(...)` (строки 108-112, перед `CKEDITOR_5_CONFIGS = {`) добавить:

```python

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ALWAYS_EAGER = 'test' in sys.argv
```

- [ ] **Step 5: Добавить сервисы `redis` и `worker` в dev docker-compose**

`docker/dev/docker-compose.yml` — полное содержимое:

```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: alexa
      POSTGRES_USER: alexa
      POSTGRES_PASSWORD: alexa
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build:
      context: ../..
      dockerfile: docker/dev/Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ../..:/app
    ports:
      - "8000:8000"
    env_file:
      - .env.dev
    environment:
      DB_HOST: db
      DJANGO_SETTINGS_MODULE: config.settings.dev
    depends_on:
      - db
      - redis

  worker:
    build:
      context: ../..
      dockerfile: docker/dev/Dockerfile
    command: celery -A config worker -l info
    volumes:
      - ../..:/app
    env_file:
      - .env.dev
    environment:
      DB_HOST: db
      DJANGO_SETTINGS_MODULE: config.settings.dev
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

- [ ] **Step 6: Добавить сервисы `redis` и `worker` в prod docker-compose**

`docker/prod/docker-compose.yml` — полное содержимое:

```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    restart: always
    env_file: .env.prod
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: always

  web:
    image: ${DOCKER_IMAGE}
    restart: always
    env_file: .env.prod
    environment:
      DB_HOST: db
      DJANGO_SETTINGS_MODULE: config.settings.prod
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  worker:
    image: ${DOCKER_IMAGE}
    restart: always
    command: celery -A config worker -l info
    env_file: .env.prod
    environment:
      DB_HOST: db
      DJANGO_SETTINGS_MODULE: config.settings.prod
    depends_on:
      - db
      - redis
    volumes:
      - media_volume:/app/media

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
      - certbot_certs:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
    depends_on:
      - web

  certbot:
    image: certbot/certbot
    restart: unless-stopped
    volumes:
      - certbot_certs:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done'"

volumes:
  postgres_data:
  static_volume:
  media_volume:
  certbot_certs:
  certbot_www:
```

(`worker` монтирует том `media_volume`, т.к. именно worker физически пишет `.webp`/`.avif` файлы на диск.)

- [ ] **Step 7: Добавить `CELERY_BROKER_URL` в env-файлы**

`docker/dev/.env.dev` — добавить строку в конец:

```
CELERY_BROKER_URL=redis://redis:6379/0
```

`docker/prod/.env.prod.example` — добавить в конец файла:

```

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
```

- [ ] **Step 8: Пересобрать образ и поднять стек**

Run: `docker-compose -f docker/dev/docker-compose.yml build web worker`
Expected: сборка проходит без ошибок, видно `Successfully installed celery-5.4.0 ... redis-5.0.8 ...`

Run: `docker-compose -f docker/dev/docker-compose.yml up -d`
Expected: контейнеры `dev-redis-1`, `dev-worker-1` запущены в дополнение к `dev-web-1`, `dev-db-1`

- [ ] **Step 9: Проверить, что worker подключился к брокеру**

Run: `docker-compose -f docker/dev/docker-compose.yml logs worker --tail=30`
Expected: в логах присутствует строка вида `celery@<hostname> ready.` и не должно быть traceback/`ConnectionError`

- [ ] **Step 10: Commit**

```bash
git add requirements.txt config/celery.py config/__init__.py config/settings/base.py \
        docker/dev/docker-compose.yml docker/prod/docker-compose.yml \
        docker/prod/.env.prod.example
git commit -m "feat: инфраструктура Celery + Redis для фоновых задач"
```

(`docker/dev/.env.dev` не отслеживается git — коммитить не нужно, но правки должны остаться на диске.)

---

### Task 2: `apps/common/tasks.py::generate_image_variants_task`

**Files:**
- Create: `apps/common/tasks.py`
- Modify: `apps/common/tests.py`

**Interfaces:**
- Consumes: `apps.common.images.generate_image_variants(field_file)` (существует)
- Produces: `apps.common.tasks.generate_image_variants_task(app_label: str, model_name: str, pk: int, field_name: str)` — Celery-задача (`@shared_task`, `autoretry_for=(Exception,)`, `max_retries=3`, `retry_backoff=True`). Загружает модель через `django.apps.apps.get_model(app_label, model_name)`, инстанс через `.objects.get(pk=pk)` (no-op, если не найден), затем — если поле `field_name` непустое — вызывает `generate_image_variants` на нём.

- [ ] **Step 1: Написать падающий тест**

Добавить в `apps/common/tests.py`:

Новые импорты в шапку файла (после существующих):

```python
from unittest.mock import patch
from django.test import override_settings
from apps.common.tasks import generate_image_variants_task
from apps.common.test_utils import make_test_image  # уже импортирован — не дублировать
from apps.doctors.models import Doctor
```

(строка `from apps.common.test_utils import FieldFileStub, make_test_image` уже существует в файле — `make_test_image` повторно не импортировать, добавить только `patch`, `override_settings`, `generate_image_variants_task`, `Doctor`.)

Новый класс в конец `apps/common/tests.py`:

```python
class GenerateImageVariantsTaskTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def test_task_loads_instance_and_generates_variants_for_field(self):
        doctor = Doctor.objects.create(
            first_name='Иван', last_name='Иванов', patronymic='Иванович',
            photo=make_test_image(name='photo.jpg'),
        )

        with patch('apps.common.tasks.generate_image_variants') as mocked:
            generate_image_variants_task('doctors', 'Doctor', doctor.pk, 'photo')

        mocked.assert_called_once()
        called_field_file = mocked.call_args[0][0]
        self.assertEqual(called_field_file.name, doctor.photo.name)

    def test_task_is_noop_for_missing_instance(self):
        with patch('apps.common.tasks.generate_image_variants') as mocked:
            generate_image_variants_task('doctors', 'Doctor', 999999, 'photo')

        mocked.assert_not_called()

    def test_task_is_noop_for_empty_field(self):
        doctor = Doctor.objects.create(
            first_name='Пётр', last_name='Петров', patronymic='Петрович',
        )

        with patch('apps.common.tasks.generate_image_variants') as mocked:
            generate_image_variants_task('doctors', 'Doctor', doctor.pk, 'photo')

        mocked.assert_not_called()
```

(В `Doctor.objects.create(photo=...)` выше `ImageVariantsMixin.save()` в текущем виде — на момент этого таска — по-прежнему вызывает `generate_image_variants` напрямую, синхронно из `apps.common.images`; это не мешает тесту, т.к. мокается ссылка `apps.common.tasks.generate_image_variants`, а не `apps.common.images.generate_image_variants`.)

- [ ] **Step 2: Запустить тест, убедиться что падает**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common.tests.GenerateImageVariantsTaskTest -v 2 --keepdb`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.common.tasks'`

- [ ] **Step 3: Реализовать `apps/common/tasks.py`**

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

- [ ] **Step 4: Запустить тест, убедиться что проходит**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common.tests.GenerateImageVariantsTaskTest -v 2 --keepdb`
Expected: `OK` — 3 теста пройдены

- [ ] **Step 5: Commit**

```bash
git add apps/common/tasks.py apps/common/tests.py
git commit -m "feat: Celery-задача generate_image_variants_task"
```

---

### Task 3: `ImageVariantsMixin` — enqueue вместо прямого вызова

**Files:**
- Modify: `apps/common/mixins.py`
- Modify: `apps/common/tests.py`

**Interfaces:**
- Consumes: `apps.common.tasks.generate_image_variants_task` (Task 2), вызывается как `generate_image_variants_task.delay(app_label, model_name, pk, field_name)`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `apps/common/tests.py` — импорт `generate_image_variants_task` уже добавлен в Task 2; дополнительно нужен `import logging` не требуется в тесте. Новый класс в конец файла:

```python
class ImageVariantsMixinEnqueueTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def test_save_enqueues_task_for_each_nonempty_field(self):
        with patch('apps.common.mixins.generate_image_variants_task') as mocked_task:
            doctor = Doctor.objects.create(
                first_name='Иван', last_name='Иванов', patronymic='Иванович',
                photo=make_test_image(name='photo.jpg'),
            )

        mocked_task.delay.assert_called_once_with('doctors', 'Doctor', doctor.pk, 'photo')

    def test_save_succeeds_even_if_enqueue_raises(self):
        with patch('apps.common.mixins.generate_image_variants_task') as mocked_task:
            mocked_task.delay.side_effect = Exception('брокер недоступен')
            doctor = Doctor.objects.create(
                first_name='Пётр', last_name='Петров', patronymic='Петрович',
                photo=make_test_image(name='photo2.jpg'),
            )

        self.assertIsNotNone(doctor.pk)
        self.assertTrue(Doctor.objects.filter(pk=doctor.pk).exists())
```

- [ ] **Step 2: Запустить тесты, убедиться что падают**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common.tests.ImageVariantsMixinEnqueueTest -v 2 --keepdb`
Expected: FAIL — `mocked_task.delay.assert_called_once_with(...)` не совпадает (миксин ещё вызывает `generate_image_variants` напрямую, а не через `generate_image_variants_task.delay`)

- [ ] **Step 3: Обновить `apps/common/mixins.py`**

```python
import logging

from apps.common.tasks import generate_image_variants_task

logger = logging.getLogger(__name__)


class ImageVariantsMixin:
    """Модель объявляет IMAGE_VARIANT_FIELDS — список имён ImageField.
    После сохранения для каждого непустого поля из списка асинхронно ставится
    задача генерации .webp/.avif вариантов (apps.common.tasks.generate_image_variants_task).
    Если постановка в очередь не удалась (брокер недоступен) — save() всё равно
    завершается успешно, ошибка только логируется.
    """

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

- [ ] **Step 4: Запустить новые тесты, убедиться что проходят**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common.tests.ImageVariantsMixinEnqueueTest -v 2 --keepdb`
Expected: `OK` — 2 теста пройдены

- [ ] **Step 5: Прогнать весь `apps.common`, убедиться что ничего не сломано**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common -v 2 --keepdb`
Expected: `OK` — все тесты `apps.common` (Task 1-3 из прошлого плана + новые) проходят

- [ ] **Step 6: Прогнать тесты всех приложений с image-полями, убедиться что `CELERY_TASK_ALWAYS_EAGER` сохраняет прежнее поведение**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.doctors apps.blog apps.promotions apps.services -v 2 --keepdb`
Expected: `OK` — все `*PictureFormatAPITest` (написанные в предыдущем плане) проходят без единой правки в их коде

- [ ] **Step 7: Commit**

```bash
git add apps/common/mixins.py apps/common/tests.py
git commit -m "feat: ImageVariantsMixin ставит генерацию вариантов в очередь Celery"
```

---

### Task 4: Финальная проверка

**Files:** нет новых/изменённых файлов — только верификация.

- [ ] **Step 1: `manage.py check`**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Полный набор тестов**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test -v 2 --keepdb`
Expected: `OK` — 0 failures/errors

- [ ] **Step 3: Живая проверка реальной асинхронности через настоящий Redis+worker**

(Тесты используют `CELERY_TASK_ALWAYS_EAGER`, поэтому не проверяют реальную доставку через брокер — этот шаг проверяет её вручную.)

Run (один скрипт: создаёт запись, проверяет что webp ещё не готов сразу после `save()`,
ждёт 3 секунды пока worker обработает задачу, проверяет что webp появился, удаляет
тестовую запись):

```bash
docker-compose -f docker/dev/docker-compose.yml exec web python manage.py shell -c "
import time
from apps.doctors.models import Doctor
from apps.common.test_utils import make_test_image

d = Doctor.objects.create(
    first_name='Тест', last_name='Асинх', patronymic='Тестович',
    photo=make_test_image(name='async_check.jpg'),
)
webp_name = d.photo.name.rsplit('.', 1)[0] + '.webp'
print('EXISTS_RIGHT_AFTER_CREATE:', d.photo.storage.exists(webp_name))

time.sleep(3)
print('EXISTS_AFTER_WAIT:', d.photo.storage.exists(webp_name))

d.delete()
"
```
Expected: `EXISTS_RIGHT_AFTER_CREATE: False` (генерация ушла в очередь, ещё не выполнена
worker'ом синхронно с `save()`), затем `EXISTS_AFTER_WAIT: True` (worker успел обработать
задачу за 3 секунды) — подтверждает, что webp появился асинхронно, уже после того как
`save()` вернул управление. Тестовая запись удаляется в конце (`d.delete()`), чтобы не
засорять реальную `media/`.

Run: `docker-compose -f docker/dev/docker-compose.yml logs worker --tail=20`
Expected: в логах worker видна обработанная задача `apps.common.tasks.generate_image_variants_task` со статусом `succeeded`

- [ ] **Step 4: Проверить отсутствие несозданных миграций**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py makemigrations --check --dry-run`
Expected: exit code 0, без вывода (модели в этой задаче не менялись — миграций быть не должно)
