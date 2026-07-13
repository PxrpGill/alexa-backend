# Генерация webp/avif-вариантов изображений при загрузке

## Контекст

Внешний фронтенд (отдельный репозиторий, в этом репо не присутствует) ожидает,
что изображения в API отдаются в формате:

```ts
export type PictureFormatDataType = {
    src: string;
    mobile?: string;
};

export type PictureFormatType = {
    original?: PictureFormatDataType;
    webp?: PictureFormatDataType;
    avif?: PictureFormatDataType;
};
```

Сейчас все `ImageField` в проекте (`doctors.Doctor.photo`, `blog.BlogPost.preview_poster`,
`blog.BlogPost.poster`, `promotions.Promotion.banner`, `services.ServiceCategory.icon`)
отдаются в API как обычная строка — URL оригинала (`resolve_<field>` возвращает
`obj.<field>.url`). Обработки изображений (Pillow используется только как зависимость
`django-ckeditor-5`/`ImageField`, но не для конвертации) в проекте нет.

## Цель

При сохранении jpg/png в любое из существующих `ImageField` автоматически генерировать
рядом `.webp` и `.avif`-копии ("нарезка форматов"). API должен отдавать структуру,
повторяющую `PictureFormatType`/`PictureFormatDataType`: `original`/`webp`/`avif`,
каждый — `{ src, mobile? }`.

`mobile` — это **не** авто-уменьшенная версия. Это отдельное изображение, которое
администратор загружает вручную (например, кадрировано по-другому под мобильный экран).
Если админ загрузил `photo_mobile`, для него так же генерируются `.webp`/`.avif`.

## 1. Модели данных

К каждому существующему `ImageField` добавляется соседнее поле `<field>_mobile`
(тот же `upload_to`, `blank=True, null=True`, русский `verbose_name` вида
"Фото (мобильная версия)"). Ручная загрузка через admin, без автоматического ресайза.

| Приложение | Существующее поле | Новое поле |
|---|---|---|
| doctors | `photo` | `photo_mobile` |
| blog | `preview_poster` | `preview_poster_mobile` |
| blog | `poster` | `poster_mobile` |
| promotions | `banner` | `banner_mobile` |
| services | `icon` | `icon_mobile` |

Требуются миграции для `doctors`, `blog`, `promotions`, `services`.

`blog/admin.py` использует явные `fieldsets` — туда нужно добавить новые mobile-поля.
Остальные три приложения используют дефолтный список полей в admin — новые поля
появятся автоматически.

## 2. Общий пакет `apps/common`

Обычный Python-пакет (без `models.py`, без регистрации в `INSTALLED_APPS`, т.к. нет
моделей/миграций):

- **`apps/common/images.py`** — `generate_image_variants(field_file)`: открывает
  изображение через Pillow, конвертирует режим при необходимости (сохраняя alpha-канал
  для PNG/icon), пишет `.webp` (quality=85) и `.avif` (quality=60, через
  `pillow-avif-plugin`) рядом с оригиналом в том же каталоге storage, с тем же basename.
  Если derived-файл с текущим именем оригинала уже существует — повторно не генерирует
  (дешёвая идемпотентность; при новой загрузке Django всегда даёт файлу новое имя,
  так что устаревший вариант никогда не будет отдан по ошибке).
- **`apps/common/mixins.py`** — `ImageVariantsMixin`: модель объявляет
  `IMAGE_VARIANT_FIELDS = ['photo', 'photo_mobile']`; миксин переопределяет `save()`,
  вызывает `super().save()`, затем для каждого поля из списка, если в нём есть файл,
  вызывает `generate_image_variants`.
- **`apps/common/schemas.py`** — Ninja-схемы, зеркалящие TS-контракт:

  ```python
  from ninja import Schema
  from typing import Optional

  class PictureFormatDataSchema(Schema):
      src: str
      mobile: Optional[str] = None

  class PictureFormatSchema(Schema):
      original: Optional[PictureFormatDataSchema] = None
      webp: Optional[PictureFormatDataSchema] = None
      avif: Optional[PictureFormatDataSchema] = None
  ```

  плюс `build_picture_format(src_field, mobile_field)` — выводит пути `.webp`/`.avif`
  из путей `src_field`/`mobile_field` (замена расширения), проверяет `storage.exists()`,
  возвращает вложенный dict (или `None`, если оригинал не загружен).

Пути webp/avif **не хранятся в БД** — выводятся из пути оригинала на лету при
сериализации. Никаких новых колонок под derived-файлы.

## 3. Подключение в моделях и схемах

- `Doctor`, `BlogPost`, `Promotion`, `ServiceCategory` получают `ImageVariantsMixin`
  и свой `IMAGE_VARIANT_FIELDS`.
- В `schemas.py` каждого из четырёх приложений: `resolve_<field>` меняется с
  `return obj.photo.url if obj.photo else None` на
  `return build_picture_format(obj.photo, obj.photo_mobile)`; тип поля меняется с
  `Optional[str]` на `Optional[PictureFormatSchema]`.

## 4. Зависимость

В `requirements.txt` добавляется `pillow-avif-plugin` (Pillow 10.4 не поддерживает AVIF
без него). `apps/common/images.py` импортирует `pillow_avif` на уровне модуля для
регистрации кодека.

## 5. Известное ограничение (вне скоупа)

Замена/очистка поля изображения не удаляет ни старый оригинал, ни его derived-файлы —
это соответствует текущему поведению проекта (оригиналы и сейчас не очищаются).
Не исправляется в рамках этой задачи как не относящееся к ней.

## 6. Тестирование

В `tests.py` каждого из четырёх приложений:
- загрузка jpg/png создаёт `.webp`/`.avif`-файлы рядом с оригиналом в storage;
- ответ API по каждому полю изображения соответствует форме `PictureFormatSchema`
  (`original.src` присутствует, `webp.src`/`avif.src` присутствуют, `mobile` заполнен
  только если была загружена мобильная версия).
