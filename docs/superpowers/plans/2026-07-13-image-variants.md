# Генерация webp/avif-вариантов изображений — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** При сохранении jpg/png в любой существующий `ImageField` автоматически генерировать рядом `.webp`/`.avif`-копии и отдавать их в API в форме `PictureFormatType` (`original`/`webp`/`avif`, каждый — `{ src, mobile? }`), где `mobile` — вручную загруженное админом отдельное изображение.

**Architecture:** Новый переиспользуемый пакет `apps/common` (зарегистрирован в `INSTALLED_APPS`, без `models.py`/миграций) содержит: `images.py` (Pillow-конвертация в webp/avif), `mixins.py` (`ImageVariantsMixin`, генерирует варианты после `save()`), `schemas.py` (Ninja-схема `PictureFormatSchema` + `build_picture_format()`, выводит пути webp/avif из пути оригинала без хранения в БД). К каждому из 5 существующих `ImageField` (doctors.photo, blog.preview_poster, blog.poster, promotions.banner, services.icon) добавляется поле `<field>_mobile`; модели используют миксин; схемы `resolve_<field>` возвращают `build_picture_format(...)`.

**Tech Stack:** Django 5.1.4, django-ninja 1.3, Pillow 10.4.0, pillow-avif-plugin 1.4.6.

## Global Constraints

- Новая зависимость: `pillow-avif-plugin==1.4.6` (Pillow 10.4 не поддерживает AVIF нативно).
- Качество конвертации: WEBP quality=85, AVIF quality=60 (константы в `apps/common/images.py`).
- Пути webp/avif **не хранятся в БД** — выводятся из пути оригинала (замена расширения) и проверяются через `storage.exists()` на лету при сериализации.
- `*_mobile` поля заполняются админом вручную, никакого автоматического ресайза/кропа.
- `apps/common` — обычный Django-app без моделей, регистрируется в `LOCAL_APPS` (`config/settings/base.py`), без миграций.
- Русский `verbose_name` на всех новых полях моделей (согласно `CLAUDE.md`).
- Тесты, загружающие реальные файлы, обязаны переопределять `MEDIA_ROOT` на временную директорию (`override_settings` + `tempfile.mkdtemp()` + очистка в `tearDown`/`tearDownClass`) — иначе тестовые файлы засоряют боевую `media/`.
- Тесты запускаются через `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test <label> -v 2 --keepdb` (см. `CLAUDE.md`/`Makefile`). Контейнер `dev-web-1` уже поднят.

---

### Task 1: `apps/common` — генерация webp/avif-вариантов (`images.py`)

**Files:**
- Create: `apps/common/__init__.py`
- Create: `apps/common/apps.py`
- Create: `apps/common/images.py`
- Create: `apps/common/test_utils.py`
- Create: `apps/common/tests.py`
- Modify: `config/settings/base.py` (добавить `'apps.common'` в `LOCAL_APPS`)
- Modify: `requirements.txt` (добавить `pillow-avif-plugin==1.4.6`)
- Modify: `docker/dev/Dockerfile` — не требуется (уже `pip install -r requirements.txt`)

**Interfaces:**
- Produces: `apps.common.images.generate_image_variants(field_file)` — принимает объект с атрибутами `.storage` (Django `Storage`) и `.name` (str, относительный путь); пишет `<basename>.webp` и `<basename>.avif` рядом в том же storage; если оба варианта уже существуют для текущего `.name` — не делает ничего.
- Produces: `apps.common.test_utils.make_test_image(name='test.jpg', img_format='JPEG', mode='RGB', size=(10, 10), content_type='image/jpeg')` → `django.core.files.uploadedfile.SimpleUploadedFile` с валидными байтами изображения.
- Produces: `apps.common.test_utils.FieldFileStub(storage, name)` — duck-type объект, имитирующий Django `FieldFile` (`.storage`, `.name`, `.url`, `__bool__`), для тестов без реальной модели.

- [ ] **Step 1: Добавить зависимость и зарегистрировать `apps.common`**

`requirements.txt` — добавить строку после `Pillow==10.4.0`:

```
Pillow==10.4.0
pillow-avif-plugin==1.4.6
```

`apps/common/__init__.py` (пустой файл):

```python
```

`apps/common/apps.py`:

```python
from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = 'Общие утилиты'
```

`config/settings/base.py` — в `LOCAL_APPS` (строка 30-38) добавить `'apps.common'` первым элементом:

```python
LOCAL_APPS = [
    'apps.common',
    'apps.users',
    'apps.branches',
    'apps.doctors',
    'apps.services',
    'apps.blog',
    'apps.promotions',
    'apps.appointments',
]
```

Пересобрать образ, т.к. поменялся `requirements.txt`:

Run: `docker-compose -f docker/dev/docker-compose.yml build web`
Expected: сборка проходит без ошибок, в логах видно `Successfully installed ... pillow-avif-plugin-1.4.6`

Run: `docker-compose -f docker/dev/docker-compose.yml up -d`
Expected: контейнер `dev-web-1` перезапущен на новом образе

- [ ] **Step 2: Написать `apps/common/test_utils.py`**

```python
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile


def make_test_image(name='test.jpg', img_format='JPEG', mode='RGB', size=(10, 10), content_type='image/jpeg'):
    buffer = BytesIO()
    Image.new(mode, size, color='red').save(buffer, format=img_format)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


class FieldFileStub:
    """Имитирует интерфейс Django FieldFile (.storage, .name, .url) без реальной модели."""

    def __init__(self, storage, name):
        self.storage = storage
        self.name = name

    def __bool__(self):
        return bool(self.name)

    @property
    def url(self):
        return self.storage.url(self.name)
```

- [ ] **Step 3: Написать падающий тест для `generate_image_variants`**

`apps/common/tests.py`:

```python
import os
import shutil
import tempfile
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase
from PIL import Image

from apps.common.images import generate_image_variants
from apps.common.test_utils import FieldFileStub, make_test_image


class GenerateImageVariantsTest(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.tmp_dir, base_url='/media/')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _save_source(self, name='doctors/photo.jpg', img_format='JPEG', mode='RGB'):
        buffer = BytesIO()
        Image.new(mode, (10, 10), color='red').save(buffer, format=img_format)
        buffer.seek(0)
        return self.storage.save(name, ContentFile(buffer.read()))

    def test_generates_webp_and_avif_siblings(self):
        saved_name = self._save_source()
        field_file = FieldFileStub(self.storage, saved_name)

        generate_image_variants(field_file)

        self.assertTrue(self.storage.exists('doctors/photo.webp'))
        self.assertTrue(self.storage.exists('doctors/photo.avif'))

    def test_preserves_transparency_for_png(self):
        saved_name = self._save_source(name='icons/icon.png', img_format='PNG', mode='RGBA')
        field_file = FieldFileStub(self.storage, saved_name)

        generate_image_variants(field_file)

        with self.storage.open('icons/icon.webp', 'rb') as f:
            webp_image = Image.open(f)
            webp_image.load()
            self.assertEqual(webp_image.mode, 'RGBA')

    def test_skips_regeneration_when_variants_already_exist(self):
        saved_name = self._save_source()
        field_file = FieldFileStub(self.storage, saved_name)
        generate_image_variants(field_file)
        webp_path = self.storage.path('doctors/photo.webp')
        first_mtime = os.path.getmtime(webp_path)

        generate_image_variants(field_file)

        self.assertEqual(os.path.getmtime(webp_path), first_mtime)
```

- [ ] **Step 4: Запустить тест, убедиться что падает**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common -v 2 --keepdb`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'apps.common.images'`

- [ ] **Step 5: Реализовать `apps/common/images.py`**

```python
import os
from io import BytesIO

import pillow_avif  # noqa: F401  — регистрирует кодек AVIF в Pillow
from django.core.files.base import ContentFile
from PIL import Image

WEBP_QUALITY = 85
AVIF_QUALITY = 60

_VARIANTS = (
    ('webp', 'WEBP', WEBP_QUALITY),
    ('avif', 'AVIF', AVIF_QUALITY),
)


def generate_image_variants(field_file):
    """Генерирует .webp и .avif рядом с оригиналом в том же storage.

    field_file — любой объект с атрибутами .storage (Django Storage) и .name
    (относительный путь), т.е. Django FieldFile или совместимый duck-type.
    Идемпотентно: если оба варианта уже существуют для текущего .name — no-op.
    """
    storage = field_file.storage
    base, _ext = os.path.splitext(field_file.name)
    variant_names = {ext: f'{base}.{ext}' for ext, _, _ in _VARIANTS}

    if all(storage.exists(name) for name in variant_names.values()):
        return

    with storage.open(field_file.name, 'rb') as source:
        image = Image.open(source)
        image.load()

    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        image = image.convert('RGBA')
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    for ext, pillow_format, quality in _VARIANTS:
        _save_variant(storage, variant_names[ext], image, pillow_format, quality)


def _save_variant(storage, name, image, pillow_format, quality):
    buffer = BytesIO()
    image.save(buffer, format=pillow_format, quality=quality)
    buffer.seek(0)
    if storage.exists(name):
        storage.delete(name)
    storage.save(name, ContentFile(buffer.read()))
```

- [ ] **Step 6: Запустить тест, убедиться что проходит**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common -v 2 --keepdb`
Expected: `OK` — 3 теста пройдены

- [ ] **Step 7: Commit**

```bash
git add apps/common/__init__.py apps/common/apps.py apps/common/images.py apps/common/test_utils.py apps/common/tests.py config/settings/base.py requirements.txt
git commit -m "feat: генерация webp/avif-вариантов изображений (apps.common)"
```

---

### Task 2: `apps/common/schemas.py` — `PictureFormatSchema` и `build_picture_format()`

**Files:**
- Create: `apps/common/schemas.py`
- Modify: `apps/common/tests.py` (дописать тесты)

**Interfaces:**
- Consumes: `apps.common.images.generate_image_variants(field_file)` (Task 1), `apps.common.test_utils.FieldFileStub`, `apps.common.test_utils.make_test_image` (Task 1)
- Produces: `apps.common.schemas.PictureFormatDataSchema` (Ninja `Schema`, поля `src: str`, `mobile: Optional[str] = None`)
- Produces: `apps.common.schemas.PictureFormatSchema` (Ninja `Schema`, поля `original`/`webp`/`avif`: `Optional[PictureFormatDataSchema] = None`)
- Produces: `apps.common.schemas.build_picture_format(src_field, mobile_field=None)` → `Optional[PictureFormatSchema]`. Возвращает `None`, если `src_field` пуст (falsy). `original` заполняется всегда (когда `src_field` не пуст), `webp`/`avif` — только если соответствующий derived-файл существует в storage.

- [ ] **Step 1: Написать падающие тесты**

Добавить один новый импорт в шапку `apps/common/tests.py` (остальные — `TestCase`, `FileSystemStorage`, `ContentFile`, `shutil`, `tempfile`, `FieldFileStub`, `make_test_image`, `generate_image_variants` — уже импортированы в Task 1, повторно не добавлять):

```python
from apps.common.schemas import build_picture_format
```

Новый класс, добавляемый в конец `apps/common/tests.py`:

```python
class BuildPictureFormatTest(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.tmp_dir, base_url='/media/')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _save(self, name, upload):
        return self.storage.save(name, ContentFile(upload.read()))

    def test_returns_none_when_no_source_file(self):
        result = build_picture_format(None)
        self.assertIsNone(result)

    def test_includes_original_webp_avif_after_generation(self):
        name = self._save('doctors/photo.jpg', make_test_image())
        field_file = FieldFileStub(self.storage, name)
        generate_image_variants(field_file)

        result = build_picture_format(field_file)

        self.assertEqual(result.original.src, '/media/doctors/photo.jpg')
        self.assertEqual(result.webp.src, '/media/doctors/photo.webp')
        self.assertEqual(result.avif.src, '/media/doctors/photo.avif')
        self.assertIsNone(result.original.mobile)

    def test_mobile_populated_when_mobile_field_given(self):
        name = self._save('doctors/photo.jpg', make_test_image())
        mobile_name = self._save('doctors/photo_m.jpg', make_test_image(name='m.jpg'))
        field_file = FieldFileStub(self.storage, name)
        mobile_field = FieldFileStub(self.storage, mobile_name)
        generate_image_variants(field_file)
        generate_image_variants(mobile_field)

        result = build_picture_format(field_file, mobile_field)

        self.assertEqual(result.original.mobile, '/media/doctors/photo_m.jpg')
        self.assertEqual(result.webp.mobile, '/media/doctors/photo_m.webp')

    def test_webp_and_avif_omitted_when_variants_missing(self):
        name = self._save('doctors/photo.jpg', make_test_image())
        field_file = FieldFileStub(self.storage, name)

        result = build_picture_format(field_file)

        self.assertIsNone(result.webp)
        self.assertIsNone(result.avif)
```

- [ ] **Step 2: Запустить тесты, убедиться что падают**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common -v 2 --keepdb`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.common.schemas'`

- [ ] **Step 3: Реализовать `apps/common/schemas.py`**

```python
import os
from typing import Optional

from ninja import Schema


class PictureFormatDataSchema(Schema):
    src: str
    mobile: Optional[str] = None


class PictureFormatSchema(Schema):
    original: Optional[PictureFormatDataSchema] = None
    webp: Optional[PictureFormatDataSchema] = None
    avif: Optional[PictureFormatDataSchema] = None


def _resolve_variant_url(field_file, extension):
    storage = field_file.storage
    base, _ext = os.path.splitext(field_file.name)
    name = f'{base}.{extension}'
    if not storage.exists(name):
        return None
    return storage.url(name)


def build_picture_format(src_field, mobile_field=None):
    if not src_field:
        return None

    mobile_original = mobile_field.url if mobile_field else None
    data = {
        'original': PictureFormatDataSchema(src=src_field.url, mobile=mobile_original),
    }

    for extension in ('webp', 'avif'):
        variant_src = _resolve_variant_url(src_field, extension)
        if variant_src is None:
            continue
        variant_mobile = _resolve_variant_url(mobile_field, extension) if mobile_field else None
        data[extension] = PictureFormatDataSchema(src=variant_src, mobile=variant_mobile)

    return PictureFormatSchema(**data)
```

- [ ] **Step 4: Запустить тесты, убедиться что проходят**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.common -v 2 --keepdb`
Expected: `OK` — 7 тестов пройдены (3 из Task 1 + 4 новых)

- [ ] **Step 5: Commit**

```bash
git add apps/common/schemas.py apps/common/tests.py
git commit -m "feat: PictureFormatSchema и build_picture_format в apps.common"
```

---

### Task 3: `apps/common/mixins.py` + подключение в `doctors`

**Files:**
- Create: `apps/common/mixins.py`
- Modify: `apps/doctors/models.py`
- Modify: `apps/doctors/schemas.py`
- Modify: `apps/doctors/tests.py`
- Create migration: `apps/doctors/migrations/0002_doctor_photo_mobile.py` (автогенерируется)

**Interfaces:**
- Consumes: `apps.common.images.generate_image_variants` (Task 1), `apps.common.schemas.PictureFormatSchema`, `apps.common.schemas.build_picture_format` (Task 2), `apps.common.test_utils.make_test_image` (Task 1)
- Produces: `apps.common.mixins.ImageVariantsMixin` — класс-миксин для моделей; подкласс объявляет `IMAGE_VARIANT_FIELDS: list[str]` (имена `ImageField`); миксин переопределяет `save()`.

- [ ] **Step 1: Реализовать `apps/common/mixins.py`**

(Отдельного теста на сам миксин не пишем — он проверяется через API-тест на `Doctor` в Step 2-6 этой задачи, т.к. миксину нужна реальная модель с `ImageField`.)

```python
from apps.common.images import generate_image_variants


class ImageVariantsMixin:
    """Модель объявляет IMAGE_VARIANT_FIELDS — список имён ImageField.
    После сохранения для каждого непустого поля из списка генерируются
    .webp/.avif варианты (см. apps.common.images.generate_image_variants).
    """

    IMAGE_VARIANT_FIELDS = []

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for field_name in self.IMAGE_VARIANT_FIELDS:
            field_file = getattr(self, field_name)
            if field_file:
                generate_image_variants(field_file)
```

- [ ] **Step 2: Написать падающий API-тест для `Doctor.photo`**

Добавить в `apps/doctors/tests.py` — новый импорт наверху файла и новый класс в конце:

```python
from apps.common.test_utils import make_test_image
```

```python
class DoctorPictureFormatAPITest(TestCase):
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

    def setUp(self):
        self.client = Client()
        self.doctor = Doctor.objects.create(
            first_name='Иван', last_name='Иванов', patronymic='Иванович',
            is_active=True,
            photo=make_test_image(name='photo.jpg'),
            photo_mobile=make_test_image(name='photo_m.jpg'),
        )
        self.doctor_no_mobile = Doctor.objects.create(
            first_name='Пётр', last_name='Петров', patronymic='Петрович',
            is_active=True,
            photo=make_test_image(name='photo2.jpg'),
        )

    def test_photo_field_matches_picture_format_shape(self):
        response = self.client.get(f'/api/v1/doctors/{self.doctor.id}/')
        self.assertEqual(response.status_code, 200)
        photo = response.json()['photo']
        self.assertTrue(photo['original']['src'].endswith('.jpg'))
        self.assertTrue(photo['original']['mobile'].endswith('.jpg'))
        self.assertTrue(photo['webp']['src'].endswith('.webp'))
        self.assertTrue(photo['webp']['mobile'].endswith('.webp'))
        self.assertTrue(photo['avif']['src'].endswith('.avif'))
        self.assertTrue(photo['avif']['mobile'].endswith('.avif'))

    def test_photo_without_mobile_has_none_mobile(self):
        response = self.client.get(f'/api/v1/doctors/{self.doctor_no_mobile.id}/')
        photo = response.json()['photo']
        self.assertIsNone(photo['original']['mobile'])
        self.assertIsNone(photo['webp']['mobile'])
```

Также добавить недостающие импорты в шапку `apps/doctors/tests.py` (`tempfile`, `shutil`, `override_settings`):

```python
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
```

(заменить существующую строку `from django.test import TestCase, Client` на строку выше).

- [ ] **Step 3: Запустить тест, убедиться что падает**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.doctors.tests.DoctorPictureFormatAPITest -v 2 --keepdb`
Expected: FAIL — `AttributeError` / `TypeError` (поля `photo_mobile` не существует)

- [ ] **Step 4: Добавить поле `photo_mobile`, подключить миксин, сделать миграцию**

`apps/doctors/models.py` — изменить импорт и объявление класса `Doctor`:

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class Specialization(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')

    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(ImageVariantsMixin, models.Model):
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    patronymic = models.CharField(max_length=100, verbose_name='Отчество')
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True, verbose_name='Фото')
    photo_mobile = models.ImageField(
        upload_to='doctors/', blank=True, null=True,
        verbose_name='Фото (мобильная версия)',
    )
    bio = CKEditor5Field(blank=True, verbose_name='Биография', config_name='default')
    specializations = models.ManyToManyField(
        Specialization, blank=True, verbose_name='Специализации'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    IMAGE_VARIANT_FIELDS = ['photo', 'photo_mobile']

    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"
```

(Классы `DoctorBranch` ниже не меняются.)

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py makemigrations doctors`
Expected: создан файл вида `apps/doctors/migrations/0002_doctor_photo_mobile.py` с `AddField('doctor', 'photo_mobile', ...)`

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py migrate`
Expected: `Applying doctors.0002_...  OK`

- [ ] **Step 5: Обновить `apps/doctors/schemas.py`**

```python
from ninja import Schema
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class SpecializationSchema(Schema):
    id: int
    name: str


class DoctorSchema(Schema):
    id: int
    first_name: str
    last_name: str
    patronymic: str
    photo: Optional[PictureFormatSchema] = None
    bio: str
    specializations: list[SpecializationSchema]
    is_active: bool

    @staticmethod
    def resolve_photo(obj):
        return build_picture_format(obj.photo, obj.photo_mobile)
```

- [ ] **Step 6: Запустить все тесты `doctors`, убедиться что проходят**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.doctors -v 2 --keepdb`
Expected: `OK` — все тесты приложения `doctors` (старые + 2 новых) проходят

- [ ] **Step 7: Commit**

```bash
git add apps/common/mixins.py apps/doctors/models.py apps/doctors/schemas.py apps/doctors/tests.py apps/doctors/migrations/
git commit -m "feat: webp/avif и mobile-версия для Doctor.photo"
```

---

### Task 4: Подключить к `blog` (`preview_poster`, `poster`)

**Files:**
- Modify: `apps/blog/models.py`
- Modify: `apps/blog/schemas.py`
- Modify: `apps/blog/admin.py`
- Modify: `apps/blog/tests.py`
- Create migration: `apps/blog/migrations/0003_...py` (автогенерируется)

**Interfaces:**
- Consumes: `apps.common.mixins.ImageVariantsMixin`, `apps.common.schemas.PictureFormatSchema`, `apps.common.schemas.build_picture_format`, `apps.common.test_utils.make_test_image` (все из Task 1-3)

- [ ] **Step 1: Написать падающий API-тест**

В `apps/blog/tests.py` заменить строку импорта:

```python
from django.test import TestCase, Client
```

на:

```python
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from apps.common.test_utils import make_test_image
```

Добавить в конец файла:

```python
class BlogPostPictureFormatAPITest(TestCase):
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

    def setUp(self):
        self.client = Client()
        category = BlogCategory.objects.create(name='Новости', slug='news-pf')
        self.post = BlogPost.objects.create(
            title='С картинками', slug='with-images', category=category,
            description='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.PUBLISHED, published_at=timezone.now(),
            preview_poster=make_test_image(name='preview.jpg'),
            preview_poster_mobile=make_test_image(name='preview_m.jpg'),
            poster=make_test_image(name='poster.jpg'),
        )

    def test_preview_poster_matches_picture_format_shape(self):
        response = self.client.get('/api/v1/blog/with-images/')
        self.assertEqual(response.status_code, 200)
        preview = response.json()['previewPoster']
        self.assertTrue(preview['original']['src'].endswith('.jpg'))
        self.assertTrue(preview['original']['mobile'].endswith('.jpg'))
        self.assertTrue(preview['webp']['src'].endswith('.webp'))

    def test_poster_without_mobile_has_none_mobile(self):
        response = self.client.get('/api/v1/blog/with-images/')
        poster = response.json()['poster']
        self.assertIsNone(poster['original']['mobile'])
        self.assertIsNone(poster['webp']['mobile'])
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.blog.tests.BlogPostPictureFormatAPITest -v 2 --keepdb`
Expected: FAIL — `TypeError` (полей `preview_poster_mobile`/`poster_mobile` не существует)

- [ ] **Step 3: Добавить mobile-поля, подключить миксин, миграция**

`apps/blog/models.py`:

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class BlogCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')

    class Meta:
        verbose_name = 'Категория блога'
        verbose_name_plural = 'Категории блога'

    def __str__(self):
        return self.name


class BlogPost(ImageVariantsMixin, models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликовано'

    title = models.CharField(max_length=500, verbose_name='Заголовок')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    category = models.ForeignKey(
        BlogCategory, on_delete=models.PROTECT,
        related_name='posts', verbose_name='Категория',
    )
    preview_poster = models.ImageField(upload_to='blog/', blank=True, verbose_name='Превью постера')
    preview_poster_mobile = models.ImageField(
        upload_to='blog/', blank=True, verbose_name='Превью постера (мобильная версия)',
    )
    poster = models.ImageField(upload_to='blog/', blank=True, verbose_name='Постер')
    poster_mobile = models.ImageField(
        upload_to='blog/', blank=True, verbose_name='Постер (мобильная версия)',
    )
    description = models.TextField(verbose_name='Описание')
    content = CKEditor5Field(config_name='blog_content', verbose_name='Контент')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, verbose_name='Статус',
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата публикации')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    IMAGE_VARIANT_FIELDS = ['preview_poster', 'preview_poster_mobile', 'poster', 'poster_mobile']

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']

    def __str__(self):
        return self.title
```

`apps/blog/admin.py` — обновить `fieldsets`:

```python
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'status')}),
        ('Контент', {
            'fields': (
                'preview_poster', 'preview_poster_mobile',
                'poster', 'poster_mobile',
                'description', 'content',
            ),
        }),
        ('Даты', {'fields': ('published_at', 'created_at')}),
    )
```

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py makemigrations blog`
Expected: создан `apps/blog/migrations/0003_...py` с двумя `AddField` (`preview_poster_mobile`, `poster_mobile`)

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py migrate`
Expected: `Applying blog.0003_...  OK`

- [ ] **Step 4: Обновить `apps/blog/schemas.py`**

```python
from ninja import Schema
from datetime import datetime
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class BlogCategorySchema(Schema):
    id: int
    name: str
    slug: str


class BlogPostListSchema(Schema):
    id: int
    title: str
    slug: str
    category: BlogCategorySchema
    previewPoster: Optional[PictureFormatSchema] = None
    poster: Optional[PictureFormatSchema] = None
    description: str
    publishDate: Optional[datetime] = None

    @staticmethod
    def resolve_previewPoster(obj):
        return build_picture_format(obj.preview_poster, obj.preview_poster_mobile)

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.poster, obj.poster_mobile)

    @staticmethod
    def resolve_publishDate(obj):
        return obj.published_at


class BlogPostDetailSchema(BlogPostListSchema):
    content: str


class PaginatedBlogPostSchema(Schema):
    items: list[BlogPostListSchema]
    page: int
    perPage: int
    total: int
    totalPages: int
```

- [ ] **Step 5: Запустить все тесты `blog`, убедиться что проходят**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.blog -v 2 --keepdb`
Expected: `OK` — все тесты приложения `blog` проходят (включая `test_list_response_uses_camel_case_fields`, не сломан)

- [ ] **Step 6: Commit**

```bash
git add apps/blog/models.py apps/blog/schemas.py apps/blog/admin.py apps/blog/tests.py apps/blog/migrations/
git commit -m "feat: webp/avif и mobile-версии для BlogPost.preview_poster/poster"
```

---

### Task 5: Подключить к `promotions` (`banner`)

**Files:**
- Modify: `apps/promotions/models.py`
- Modify: `apps/promotions/schemas.py`
- Modify: `apps/promotions/tests.py`
- Create migration: `apps/promotions/migrations/0002_...py` (автогенерируется)

**Interfaces:**
- Consumes: `apps.common.mixins.ImageVariantsMixin`, `apps.common.schemas.PictureFormatSchema`, `apps.common.schemas.build_picture_format`, `apps.common.test_utils.make_test_image`

- [ ] **Step 1: Написать падающий API-тест**

В `apps/promotions/tests.py` заменить строку импорта:

```python
from django.test import TestCase, Client
```

на:

```python
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from apps.common.test_utils import make_test_image
```

Добавить в конец файла:

```python
class PromotionPictureFormatAPITest(TestCase):
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

    def setUp(self):
        self.client = Client()
        today = date.today()
        self.promo = Promotion.objects.create(
            title='Акция с баннером',
            starts_at=today - timedelta(days=1),
            ends_at=today + timedelta(days=5),
            is_active=True,
            banner=make_test_image(name='banner.jpg'),
            banner_mobile=make_test_image(name='banner_m.jpg'),
        )

    def test_banner_matches_picture_format_shape(self):
        response = self.client.get('/api/v1/promotions/')
        self.assertEqual(response.status_code, 200)
        promo = next(p for p in response.json() if p['title'] == 'Акция с баннером')
        banner = promo['banner']
        self.assertTrue(banner['original']['src'].endswith('.jpg'))
        self.assertTrue(banner['original']['mobile'].endswith('.jpg'))
        self.assertTrue(banner['webp']['src'].endswith('.webp'))
        self.assertTrue(banner['avif']['src'].endswith('.avif'))
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.promotions.tests.PromotionPictureFormatAPITest -v 2 --keepdb`
Expected: FAIL — `TypeError` (поля `banner_mobile` не существует)

- [ ] **Step 3: Добавить mobile-поле, подключить миксин, миграция**

`apps/promotions/models.py`:

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class Promotion(ImageVariantsMixin, models.Model):
    title = models.CharField(max_length=500, verbose_name='Заголовок')
    description = CKEditor5Field(config_name='default', blank=True, verbose_name='Описание')
    banner = models.ImageField(upload_to='promotions/', blank=True, verbose_name='Баннер')
    banner_mobile = models.ImageField(
        upload_to='promotions/', blank=True, verbose_name='Баннер (мобильная версия)',
    )
    starts_at = models.DateField(verbose_name='Начало')
    ends_at = models.DateField(null=True, blank=True, verbose_name='Окончание')
    branches = models.ManyToManyField(
        'branches.Branch', blank=True,
        related_name='promotions', verbose_name='Филиалы',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    IMAGE_VARIANT_FIELDS = ['banner', 'banner_mobile']

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'
        ordering = ['-starts_at']

    def __str__(self):
        return self.title
```

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py makemigrations promotions`
Expected: создан `apps/promotions/migrations/0002_promotion_banner_mobile.py`

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py migrate`
Expected: `Applying promotions.0002_...  OK`

- [ ] **Step 4: Обновить `apps/promotions/schemas.py`**

```python
from ninja import Schema
from datetime import date
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class PromotionSchema(Schema):
    id: int
    title: str
    banner: Optional[PictureFormatSchema] = None
    starts_at: date
    ends_at: Optional[date] = None
    is_active: bool

    @staticmethod
    def resolve_banner(obj):
        return build_picture_format(obj.banner, obj.banner_mobile)
```

- [ ] **Step 5: Запустить все тесты `promotions`, убедиться что проходят**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.promotions -v 2 --keepdb`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add apps/promotions/models.py apps/promotions/schemas.py apps/promotions/tests.py apps/promotions/migrations/
git commit -m "feat: webp/avif и mobile-версия для Promotion.banner"
```

---

### Task 6: Подключить к `services` (`ServiceCategory.icon`)

**Files:**
- Modify: `apps/services/models.py`
- Modify: `apps/services/schemas.py`
- Modify: `apps/services/tests.py`
- Create migration: `apps/services/migrations/0002_...py` (автогенерируется)

**Interfaces:**
- Consumes: `apps.common.mixins.ImageVariantsMixin`, `apps.common.schemas.PictureFormatSchema`, `apps.common.schemas.build_picture_format`, `apps.common.test_utils.make_test_image`

- [ ] **Step 1: Написать падающий API-тест**

В `apps/services/tests.py` заменить строку импорта:

```python
from django.test import TestCase, Client
```

на:

```python
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from apps.common.test_utils import make_test_image
```

Добавить в конец файла:

```python
class ServiceCategoryPictureFormatAPITest(TestCase):
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

    def setUp(self):
        self.client = Client()
        self.category = ServiceCategory.objects.create(
            name='Хирургия', slug='surgery-pf',
            icon=make_test_image(name='icon.png', img_format='PNG', content_type='image/png'),
            icon_mobile=make_test_image(name='icon_m.png', img_format='PNG', content_type='image/png'),
        )

    def test_icon_matches_picture_format_shape(self):
        response = self.client.get('/api/v1/services/categories/')
        self.assertEqual(response.status_code, 200)
        category = next(c for c in response.json() if c['slug'] == 'surgery-pf')
        icon = category['icon']
        self.assertTrue(icon['original']['src'].endswith('.png'))
        self.assertTrue(icon['original']['mobile'].endswith('.png'))
        self.assertTrue(icon['webp']['src'].endswith('.webp'))
        self.assertTrue(icon['avif']['src'].endswith('.avif'))
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.services.tests.ServiceCategoryPictureFormatAPITest -v 2 --keepdb`
Expected: FAIL — `TypeError` (поля `icon_mobile` не существует)

- [ ] **Step 3: Добавить mobile-поле, подключить миксин, миграция**

`apps/services/models.py` — изменить импорт и `ServiceCategory`:

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.common.mixins import ImageVariantsMixin


class ServiceCategory(ImageVariantsMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    icon = models.ImageField(upload_to='service_categories/', blank=True, verbose_name='Иконка')
    icon_mobile = models.ImageField(
        upload_to='service_categories/', blank=True, verbose_name='Иконка (мобильная версия)',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    IMAGE_VARIANT_FIELDS = ['icon', 'icon_mobile']

    class Meta:
        verbose_name = 'Категория услуг'
        verbose_name_plural = 'Категории услуг'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
```

(Классы `Service` и `BranchService` ниже не меняются.)

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py makemigrations services`
Expected: создан `apps/services/migrations/0002_servicecategory_icon_mobile.py`

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py migrate`
Expected: `Applying services.0002_...  OK`

- [ ] **Step 4: Обновить `apps/services/schemas.py`**

```python
from ninja import Schema
from decimal import Decimal
from typing import Optional
from apps.common.schemas import PictureFormatSchema, build_picture_format


class ServiceCategorySchema(Schema):
    id: int
    name: str
    slug: str
    icon: Optional[PictureFormatSchema] = None

    @staticmethod
    def resolve_icon(obj):
        return build_picture_format(obj.icon, obj.icon_mobile)


class ServiceWithPriceSchema(Schema):
    id: int
    name: str
    slug: str
    category_id: int
    price: Decimal
    price_from: bool
```

- [ ] **Step 5: Запустить все тесты `services`, убедиться что проходят**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test apps.services -v 2 --keepdb`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add apps/services/models.py apps/services/schemas.py apps/services/tests.py apps/services/migrations/
git commit -m "feat: webp/avif и mobile-версия для ServiceCategory.icon"
```

---

### Task 7: Финальная проверка всего проекта

**Files:** нет новых/изменённых файлов — только верификация.

- [ ] **Step 1: Прогнать `manage.py check`**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Прогнать весь набор тестов**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test -v 2 --keepdb`
Expected: `OK` — все тесты проекта (старые + новые из Task 1-6) проходят, 0 failures/errors

- [ ] **Step 3: Убедиться что миграции применены и нет расхождений**

Run: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py makemigrations --check --dry-run`
Expected: exit code 0, без вывода (нет несозданных миграций)
