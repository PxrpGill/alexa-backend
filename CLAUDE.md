# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Django 5.1.4 + django-ninja backend стоматологической клиники «Алекса»: мультифилиальная
структура, ролевая admin-панель на jazzmin, публичный REST API без аутентификации
(потребитель — Next.js фронтенд). Язык проекта — русский: `verbose_name`, docstrings,
сообщения об ошибках API и commit-сообщения на русском.

`AGENTS.md` описывает тот же проект короче — при изменении конвенций правь оба файла.

## Команды

Всё выполняется внутри контейнера `web`; локального запуска без Docker нет.

```bash
make dev-up                    # db + redis + web(runserver) + worker(celery)
make dev-down / dev-logs / dev-shell
make dev-check                 # manage.py check
make dev-test                  # manage.py test -v 2 --keepdb
make dev-test-app APP=vacancies
make dev-migrate APP=vacancies # makemigrations <короткое имя> && migrate
```

Один тест-класс или метод — напрямую через compose:

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.vacancies.tests.ApplicationAPITest.test_apply_ok -v 2 --keepdb
```

- `--keepdb` обязателен: тестовая БД живёт в docker-volume, пересоздание долгое.
- Линтера/типизации нет (есть только `.ruff_cache` от ручных запусков). Проверка — `make dev-check` + тесты.
- Makefile использует standalone-бинарь `docker-compose` (не `docker compose`).
- Дев-точки входа: API docs `/api/v1/docs`, OpenAPI `/api/v1/openapi.json`, admin `/admin/`.

## Настройки и точки расширения

- `config/settings/{base,dev,prod}.py`; `DJANGO_SETTINGS_MODULE` по умолчанию
  `config.settings.dev` (задан в `manage.py` и `config/celery.py`), в compose — явно.
- Новое приложение → добавить в `LOCAL_APPS` в `base.py`. Порядок `INSTALLED_APPS`:
  `jazzmin` строго перед `django.contrib.admin`.
- Новый роутер → импорт + `api.add_router("/name", router)` в `config/api.py`.
- Новая модель в admin → иконка в `JAZZMIN_SETTINGS['icons']` (`app.model` в нижнем регистре).
- `.env` читается через `python-decouple`; шаблон — `.env.example`, дев-значения —
  `docker/dev/.env.dev`, прод — `docker/prod/.env.prod.example`.

## Приложения

| App | Содержимое | API |
|---|---|---|
| `common` | инфраструктура: `ImageVariantsMixin`, `images.py`, `tasks.py`, `throttling.py`, `typography.py`, общие схемы, `test_utils.py` | — |
| `users` | `User(AbstractUser)` + `Role` (только роли, **без** FK на филиал) | — |
| `branch` | `BranchModel` — филиалы | `GET /branches/` |
| `doctors` | `Doctor`, `Specialization` | `GET /doctors/`, `/doctors/{id}/` |
| `blog` | `BlogCategory`, `BlogPost` (+ типографика в `save()`) | `GET /blog`, `/blog/{slug}` |
| `promotions` | `Promotion`, `PromotionRequests` | `GET /promotions`, `POST /promotions/request` |
| `appointments` | `Appointment` + signal уведомления в MAX (`signals.py`, подключён в `apps.py:ready()`) | `POST /appointments` |
| `dms` | `DMS` — заявки ДМС | `POST /dms` |
| `consultation` | `Consultation` | `POST /consultation` |
| `vacancies` | `VacancyCategory`, `Vacancy` + 5 inline-моделей, `Application`, `validators.py` | `GET /vacancies`, `/vacancies/{slug}`, `POST /vacancies/apply`, `/vacancies/{slug}/apply` |

Каждое приложение содержит `models.py`, `admin.py`, `api.py`, `schemas.py`
(в `branch` файл называется `schema.py`), опционально `tests.py`.

Приложений `apps/branches` и `apps/services` **нет** — они удалены; старые планы в
`docs/superpowers/` и `.claude/PROJECT_MEMORY.md` описывают ту версию и неактуальны.

## Ключевые конвенции

### Филиалы
- Модель называется `BranchModel`, cross-app FK — **прямым импортом** (`from apps.branch.models import BranchModel`), а не строкой `'branch.BranchModel'`.
- PK — `UUIDField`; `slug` генерируется в `save()` транслитерацией имени (`pytils` + `slugify`) с суффиксом `-N` при коллизии. Тот же паттерн повторён в `Vacancy`/`VacancyCategory`/`Promotion`.
- В API филиал всегда выбирается по **slug**: `get_object_or_404(BranchModel, slug=payload.branch_slug)`, никогда по id.

### Пути endpoint'ов
`APPEND_SLASH = False`, поэтому путь в декораторе — это ровно путь запроса. В коде две
сложившиеся группы, не унифицированы:
- `doctors`, `branch` — со слэшем: `@router.get('/')`, `@router.get('/{doctor_id}/')`.
- `blog`, `promotions`, `vacancies`, lead-формы — без: `@router.get("")`, `@router.get("/{slug}")`.

При правке endpoint сохраняй форму пути его приложения — тесты и фронтенд бьют по точным URL.

### Изображения: автоматические webp/avif
Модель с картинками наследует `ImageVariantsMixin` (`apps/common/mixins.py`) и объявляет
`IMAGE_VARIANT_FIELDS = ['photo', 'photo_mobile']`. После `save()` ставится Celery-задача
`generate_image_variants_task`, которая кладёт `.webp`/`.avif` рядом с оригиналом
(`apps/common/images.py`, нужен `pillow_avif`). Постановка в очередь обёрнута в try/except:
недоступный брокер не ломает `save()`.

В схемах картинки отдаются **только** через `build_picture_format(obj.photo, obj.photo_mobile)`
→ `PictureFormatSchema` = `{original, webp, avif}`, каждый `{src, mobile}`. Сырые `.url` не
возвращаем. Вариант попадает в ответ лишь если файл реально существует в storage.

Под тестами Celery — eager (`CELERY_TASK_ALWAYS_EAGER = "test" in sys.argv` в `base.py`),
т.е. варианты генерируются синхронно.

### Lead-формы (appointments, dms, consultation, promotions/request)
Один и тот же контракт, эталон — `apps/appointments/api.py`:
1. нет `payload.is_privacy_agreement` → `400` + `ErrorResponseMessageSchema`;
2. филиал по slug (в `promotions/request` — акция по slug);
3. создать запись, сохранив `is_ad_agreement` / `is_privacy_agreement`, `page_url` через `request.build_absolute_uri()`;
4. `response={201: SuccessResponseMessageSchema, 400: ErrorResponseMessageSchema}`.

Новый lead-endpoint повторяет эту форму. Исключение — `vacancies`: там валидация вынесена
в `apps/vacancies/validators.py` и ответ 400 — словарь `{field: [messages]}` (`ApplicationErrorSchema`),
загрузка резюме идёт `multipart/form-data` (`Form(...)` + `File(None)`) с проверкой
расширения, MIME, `settings.MAX_RESUME_SIZE` и magic-байтов.

### Уведомления о заявках в MAX
Каждая модель заявки шлёт уведомление в общий чат мессенджера MAX через
`post_save`-receiver в `signals.py` своего приложения (`apps.py:ready()` его импортирует).
Receiver передаёт заголовок и строки в `queue_lead_notification()` (`apps/common/max.py`):
она собирает текст `format_lead_message()` под `try/except` и ставит задачу после коммита.
Отправка идёт Celery-задачей `send_max_notification_task` с 3 ретраями. Ни сбой сборки
текста, ни лежащий брокер, ни падение MAX не ломают `save()` и ответ API — иначе пациент
увидел бы ошибку на сохранённой заявке и отправил форму повторно.
Ошибки доставки заворачиваются в `MaxDeliveryError`: токен идёт в URL query-параметром
и из текста исключения `requests` утёк бы в логи.

Выключено, пока не заданы `MAX_BOT_TOKEN` и `MAX_CHAT_ID` (`MAX_NOTIFICATIONS_ENABLED`),
поэтому дев и CI никуда не стучатся. Ссылка на запись в админке строится из `SITE_URL`.
Файл резюме в чат не отправляется — это защищённые ПД, только пометка «приложено».
Сигнал срабатывает и на запись, заведённую руками в админке — это осознанно.

Новый тип заявки → `signals.py` по образцу `apps/appointments/signals.py` + `ready()`
+ тест с `captureOnCommitCallbacks` и моком `send_max_notification_task.delay`.

### Throttling
`@throttle_lead_form` из `apps/common/throttling.py` — 10 отправок с одного IP в минуту;
навешивается на **каждый** публичный POST формы (appointments, dms, consultation,
promotions/request, отклики на вакансии). Роут обязан объявить
`429: ErrorResponseMessageSchema` — это проверяет `tests/test_api_smoke.py`.
Для нестандартных лимитов есть базовый `@throttle(limit, window_seconds, message=...)`.

IP берётся через `get_client_ip()`: за nginx `REMOTE_ADDR` — это адрес контейнера
прокси, один на всех, поэтому читаются `X-Real-IP` и **последний** элемент
`X-Forwarded-For` (начало цепочки клиент может подделать). Включено настройкой
`TRUST_PROXY_HEADERS` (по умолчанию = `not DEBUG`). Под тестами throttle не действует.

Порядок декораторов: `@router.post(...)` сверху, `@throttle_lead_form` под ним —
ninja достаёт исходную сигнатуру через `functools.wraps`.

### Защищённые файлы
Резюме откликов (`vacancies/resumes/`) — персональные данные: каталог объявлен
`internal` в nginx, прямые ссылки на `/media/...` дают 404. Выдача идёт через
`apps/vacancies/views.download_resume` (`@staff_member_required`) —
X-Accel-Redirect в проде и `FileResponse` в dev (`USE_X_ACCEL_REDIRECT`).
В админке вместо файлового поля — колонка-ссылка `resume_link`.
Новые приватные файлы подключать так же, а не через публичный `/media/`.

### Прочее
- `BlogPost.save()` прогоняет текст через `apps/common/typography.py` (`typograph_text` / `typograph_html`, вырезает `style`-атрибуты) — при переопределении `save()` не потерять.
- Список блога — своя пагинация: query-параметры `page`, `perPage`, `allPages`, ответ `PaginatedBlogPostSchema` (`items` + `pagination`), а не плоский список.
- Список вакансий: без `?category=` подставляется первая активная категория; в `categories` попадают только категории с опубликованными вакансиями; `total` — по всем категориям.
- Акции фильтруются по `timezone.localdate()`, `ends_at__isnull=True` = бессрочная.
- Прод-инфраструктура: `docker/prod/nginx/default.conf.template` — шаблон, домен подставляется из `DOMAIN` в `.env.prod` через envsubst образа nginx (`NGINX_ENVSUBST_FILTER=DOMAIN`, каталог монтируется в `/etc/nginx/templates`). Правки конфига едут обычным деплоем. Имя compose-проекта закреплено как `prod` — менять только с миграцией томов.
- `list`-endpoint'ы фильтруют публикуемость (`is_active` / `is_published` / `status=PUBLISHED`), detail на скрытой записи → 404.
- `select_related` для FK, `prefetch_related` для M2M/inline, `.distinct()` при JOIN через M2M.
- `BranchFilterMixin` / `apps/users/mixins.py` больше не существуют: admin по филиалам не ограничивается, `User.role` пока нигде не влияет на queryset.

## Тесты

`tests/test_api_smoke.py` проверяет доступность `/api/v1/docs` и наличие путей в
`openapi.json` — при переименовании роутов его нужно обновлять. Содержательные тесты есть
в `apps/common`, `apps/vacancies`, `apps/blog`, `apps/users`; `apps/dms/tests.py` и
`apps/consultation/tests.py` — пустые заготовки. Хелперы для картинок —
`apps/common/test_utils.py` (`make_test_image`, `FieldFileStub`).

## Git и деплой

Ветки `feat/*` → PR → merge в `main`. Push в `main` запускает
`.github/workflows/deploy.yml`: job `test` (postgres + redis services, `check --deploy`
и `manage.py test` — красные тесты блокируют деплой) → сборка `docker/prod/Dockerfile`
→ push в GHCR → SSH на VPS (`/opt/alexa-backend`) → `git pull`, `compose pull/up -d`,
`migrate`, `collectstatic`, `nginx -s reload`.
Прод-стек: postgres 16 · redis · gunicorn · celery worker · nginx + certbot.
Подробности — `docs/deploy.md`, `docs/docker.md`.
