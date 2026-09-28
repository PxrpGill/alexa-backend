# Alexa Backend

Backend сети стоматологических клиник «Алекса»: админка для управления контентом
и публичный REST API для сайта на Next.js.

Что умеет:

- **Контент клиники** — филиалы, врачи, блог, акции, вакансии; редактируется в
  админке, отдаётся фронтенду через API.
- **Заявки** — запись на приём, ДМС, консультация, заявка на акцию, отклик на
  вакансию с загрузкой резюме. Все формы публичные, с rate limit по IP.
- **Изображения** — при загрузке рядом с оригиналом автоматически генерируются
  `.webp` и `.avif` (Celery), API отдаёт все варианты сразу.

## Стек

| | |
|---|---|
| Django 5.1 + django-ninja 1.3 | приложение и REST API (схемы в стиле FastAPI) |
| PostgreSQL 16 | БД |
| Redis + Celery | очередь для обработки изображений, кэш для rate limit |
| django-jazzmin | UI админки |
| django-ckeditor-5 | rich-text поля |
| Docker Compose | dev и прод одинаково поднимаются контейнерами |

Python 3.12, локально ничего кроме Docker не нужно.

## Быстрый старт

```bash
git clone https://github.com/PxrpGill/alexa-backend.git
cd alexa-backend
```

Окружение для dev лежит в `.gitignore`, поэтому в свежем клоне его нет — создать
как есть (хосты `db` и `redis` — это имена сервисов в compose-сети):

```bash
cat > docker/dev/.env.dev <<'EOF'
SECRET_KEY=django-insecure-dev-only-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,host.docker.internal
DB_NAME=alexa
DB_USER=alexa
DB_PASSWORD=alexa
DB_HOST=db
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000
CELERY_BROKER_URL=redis://redis:6379/0
REDIS_URL=redis://redis:6379/1
EOF
```

Полный список переменных с комментариями — в [.env.example](.env.example).

```bash
make dev-up                                                     # db, redis, web, worker
docker compose -f docker/dev/docker-compose.yml exec web python manage.py migrate
docker compose -f docker/dev/docker-compose.yml exec web python manage.py createsuperuser
```

- Админка — http://localhost:8000/admin/
- Документация API (Swagger) — http://localhost:8000/api/v1/docs
- Схема OpenAPI — http://localhost:8000/api/v1/openapi.json

Код смонтирован в контейнер, `runserver` перезагружается сам — пересобирать образ
после правок не нужно.

## Команды

```bash
make dev-up / dev-down / dev-logs      # поднять, остановить, смотреть логи web
make dev-shell                         # python manage.py shell
make dev-check                         # manage.py check
make dev-test                          # все тесты
make dev-test-app APP=vacancies        # тесты одного приложения
make dev-migrate APP=vacancies         # makemigrations <app> && migrate
```

Цели Makefile вызывают отдельный бинарь `docker-compose`, а не плагин
`docker compose`. Если его нет (в свежем Docker Desktop его не ставят), либо
поставьте бинарь, либо работайте через `docker compose -f docker/dev/docker-compose.yml …`.

Тесты идут с `--keepdb`: тестовая БД лежит в docker-томе и не пересоздаётся
каждый раз. Один тест — напрямую через compose:

```bash
docker compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.vacancies.tests.ResumeDownloadTest -v 2 --keepdb
```

## API

Базовый URL — `/api/v1/`, аутентификации нет: информация о клинике публичная.
Списки отдают только опубликованные записи, detail на скрытой записи → 404.

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/branches/` | филиалы |
| GET | `/doctors/`, `/doctors/{id}/` | врачи и специализации |
| GET | `/blog?page=&perPage=&allPages=` | статьи блога с пагинацией |
| GET | `/blog/{slug}` | статья |
| GET | `/promotions` | действующие на сегодня акции |
| POST | `/promotions/request` | заявка на акцию |
| POST | `/appointments` | запись на приём |
| POST | `/dms` | заявка по ДМС |
| POST | `/consultation` | заявка на консультацию |
| GET | `/vacancies?category=<slug>` | вакансии по категориям |
| GET | `/vacancies/{slug}` | вакансия |
| POST | `/vacancies/apply`, `/vacancies/{slug}/apply` | отклик с резюме (multipart) |

Особенности, о которых стоит знать заранее:

- `APPEND_SLASH = False`, и пути неоднородны: у `doctors` и `branches` они со
  слэшем, у остальных — без. Бить нужно точно по указанному пути.
- Филиал в формах передаётся строкой `branch_slug`, не идентификатором.
- Любая форма требует `is_privacy_agreement: true` (в вакансиях —
  `privacy_policy_accepted`), иначе `400`.
- Лимит 10 отправок формы с одного IP в минуту, при превышении `429`.
- Картинки приходят объектом `{original, webp, avif}`, внутри каждого
  `{src, mobile}` — фронтенд собирает из этого `<picture>`.

Пример:

```bash
curl -X POST http://localhost:8000/api/v1/consultation \
  -H 'Content-Type: application/json' \
  -d '{"patient_name":"Иван","patient_phone":"+79991234567",
       "branch_slug":"landyshevaya","is_privacy_agreement":true}'
```

## Структура

```
apps/
  common/        общая инфраструктура: варианты изображений, throttling,
                 типографика, общие схемы ответов
  users/         User с ролями superadmin / branch_manager
  branch/        филиалы (BranchModel, UUID + slug)
  doctors/       врачи и специализации
  blog/          категории и статьи
  promotions/    акции и заявки на них
  appointments/  записи на приём (+ заготовка уведомления в Telegram)
  dms/           заявки по ДМС
  consultation/  заявки на консультацию
  vacancies/     вакансии, отклики, валидация резюме
config/
  settings/      base / dev / prod
  api.py         корневой роутер — сюда добавляются новые
  urls.py        admin, API, ckeditor, защищённая выдача резюме
docker/
  dev/ prod/     compose-файлы, Dockerfile, конфиг nginx
docs/            deploy.md, docker.md
```

Приложения устроены одинаково: `models.py`, `admin.py`, `api.py`, `schemas.py`,
`tests.py`. Все `verbose_name`, docstrings и сообщения об ошибках — на русском.

## Деплой

Merge в `main` запускает [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml):
тесты → сборка образа → push в GHCR → SSH на VPS, `migrate`, `collectstatic`,
перезагрузка nginx. Прод — тот же compose плюс nginx и certbot.

Полная инструкция от чистого VPS до работающего HTTPS — [docs/deploy.md](docs/deploy.md),
разбор Docker-окружений — [docs/docker.md](docs/docker.md).

## Дальше

- [CLAUDE.md](CLAUDE.md) — конвенции проекта: как добавлять приложение, роутер,
  форму-заявку, как работают варианты изображений и защищённые файлы. Читать
  перед первой задачей.
- [AGENTS.md](AGENTS.md) — то же короче, для AI-агентов.
