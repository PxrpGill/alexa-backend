---
name: alexa_backend_project
description: Alexa Backend — Django 5.1 + Ninja API для стоматологической клиники, 9 задач на TDD, дизайн и план готовы
metadata:
  type: project
---

## 📋 Статус проекта

**Статус:** Готов к выполнению — дизайн и план готовы, все 9 задач ждут выполнения  
**Подход:** Subagent-driven development + TDD (test-first)  
**Начало:** 2026-06-23, коммит плана: 7ad7bc0

## 🎯 Цель

Создать Django + Ninja backend для стоматологии «Алекса» с:
- Мультифилиальной архитектурой (несколько кабинетов)
- Ролевой admin-панелью на Jazzmin (супер-админ и менеджеры филиалов)
- Публичным REST API `/api/v1/` для Next.js фронтенда

## 🛠️ Технологический стек

- **Python 3.12**
- **Django 5.1.4** (не ниже)
- **django-ninja 1.3** — REST API
- **django-jazzmin 3.0** — красивая админка
- **django-ckeditor-5** — WYSIWYG редактор
- **PostgreSQL 16** — база данных
- **Pillow** — обработка изображений
- **gunicorn** — WSGI сервер
- **django-cors-headers** — CORS для фронтенда

## 🏗️ Архитектура

Feature-based структура. Каждый app содержит:
- `models.py` — ORM модели
- `admin.py` — админ с BranchFilterMixin
- `api.py` — Ninja роутер
- `schemas.py` — request/response схемы
- `tests.py` — unit тесты (TDD first!)

**Глобальные constraint'ы:**
- `AUTH_USER_MODEL = 'users.User'` (задаётся до первой миграции)
- Все FK на Branch используют строковые ссылки `'branches.Branch'`
- Все API эндпоинты публичны (кроме аутентификации пока нет)
- Медиафайлы в `media/` корне проекта
- CORS для `http://localhost:3000` (фронтенд)
- Prefix: `/api/v1/`

## 📦 7 приложений (apps)

| #  | App | Модели | API endpoints | Примечание |
|----|----|--------|---------------|-----------|
| 1  | `users` | User (кастом) | —— | AUTH_USER_MODEL, role + branch FK |
| 2  | `branches` | Branch | GET /branches/, GET /branches/{id}/ | Филиалы клиники |
| 3  | `doctors` | Doctor, Specialization, DoctorBranch | GET /doctors/, GET /doctors/{id}/, фильтр ?branch_id= | Врачи + специализации |
| 4  | `services` | ServiceCategory, Service, BranchService | GET /services/, GET /services/categories/, фильтры | Услуги + цены по филиалам |
| 5  | `blog` | BlogCategory, BlogPost | GET /blog/, GET /blog/{slug}/ | Статьи (CKEditor5) |
| 6  | `promotions` | Promotion | GET /promotions/, фильтр ?branch_id= | Акции с датами (only active) |
| 7  | `appointments` | Appointment | POST /appointments/ | Запись к врачу (сигнал → Telegram stub) |

## ✅ 9 задач (все в разработке)

| # | Task | Файлы | Статус | Примечание |
|---|------|-------|--------|-----------|
| 1 | Project Scaffolding | requirements.txt, .env, Dockerfile, config/* | ⏳ | Django 5.1 + Ninja setup |
| 2 | Users App | users/* | ⏳ | Custom User model (TDD) |
| 3 | Branches App | branches/*, config/api.py | ⏳ | Филиалы + API |
| 4 | Doctors App | doctors/*, config/api.py | ⏳ | Врачи + специализации |
| 5 | Services App | services/*, config/api.py | ⏳ | Услуги + цены |
| 6 | Blog App | blog/*, config/api.py | ⏳ | Блог (CKEditor5) |
| 7 | Promotions App | promotions/*, config/api.py | ⏳ | Акции с датами |
| 8 | Appointments App | appointments/*, config/api.py | ⏳ | Запись на приём |
| 9 | Admin Polish + Wiring | config/settings/base.py (JAZZMIN_*), tests/test_api_smoke.py | ⏳ | Финализация |

## 🧪 Подход: Test-Driven Development

Каждая задача следует TDD цикл:
1. Написать **failing test** (ImportError / AssertionError)
2. Убедиться, что тест падает ✗
3. Реализовать код (models, admin, schemas, api)
4. Запустить тесты — все проходят ✓
5. Коммит

Каждый app имеет минимум 2-4 теста:
- Model tests (создание, __str__, relations)
- API tests (GET/POST, фильтры, 404)

## 📍 Файловая структура

```
alexa-backend/
├── config/
│   ├── __init__.py
│   ├── api.py               ← Регистрация всех роутеров
│   ├── urls.py
│   ├── settings/
│   │   ├── base.py          ← AUTH_USER_MODEL, INSTALLED_APPS
│   │   ├── dev.py
│   │   └── prod.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── users/
│   ├── branches/
│   ├── doctors/
│   ├── services/
│   ├── blog/
│   ├── promotions/
│   └── appointments/
├── tests/
│   └── test_api_smoke.py    ← Финальная smoke-тестя
├── requirements.txt
├── .env
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

## 🚀 Как выполнять задачи

**Рекомендация:** Использовать `/superpowers:subagent-driven-development`

Каждая задача — это milestone:
1. Создать структуру (mkdir, touch)
2. Написать failing тест
3. Убедиться что тест падает (`python manage.py test apps.xxx.tests -v 2`)
4. Реализовать код (models → schemas → admin → api)
5. Запустить миграции (`python manage.py makemigrations xxx && python manage.py migrate`)
6. Все тесты зелёные ✓
7. Коммит с понятным сообщением

## 🔍 Ключевые детали

- **BranchFilterMixin** (в users/mixins.py) — ограничивает админ-доступ менеджеров только их филиалом
- **Сигнал в appointments** — на post_save отправлять в Telegram (пока stub)
- **Jazzmin icons** — каждый app имеет свой FontAwesome иконку
- **CORS** — разрешено только localhost:3000
- **Все тесты** должны проходить: `python manage.py test -v 2` (ожидается ~21 тест)
- **Финальная проверка:**
  - `python manage.py check` — no issues
  - `python manage.py check --deploy` — всё ок
  - GET /api/v1/docs/ — видны все 6 секций эндпоинтов

## 📚 Документация

- **План:** docs/superpowers/plans/2026-06-23-alexa-backend.md
- **Дизайн-спек:** docs/superpowers/specs/2026-06-23-alexa-backend-design.md
- **Progress:** .superpowers/sdd/progress.md

## 💡 Особенности

- Все API публичные (аутентификация планируется позже)
- Doctor → Branch через junction table DoctorBranch (schedule, is_active)
- Service → Branch через junction table BranchService (цены разные по филиалам)
- Promotion → Branch через M2M (акции на определённые филиалы)
- Blog & Promotions используют CKEditor5 для rich text
- Appointment сигнал = позже интегрировать Telegram bot
