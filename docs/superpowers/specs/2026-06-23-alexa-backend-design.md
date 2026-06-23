# Alexa Backend — Design Spec

**Date:** 2026-06-23
**Project:** Стоматологическая клиника «Алекса» — Backend
**Stack:** Django + Django Ninja + PostgreSQL

---

## 1. Overview

Backend для сайта семейной стоматологии «Алекса». Предоставляет:

- REST API (Django Ninja) для Next.js-фронтенда (`alexa-webapp`, `http://localhost:8000`)
- Административную панель (django-jazzmin) для управления контентом
- Мультифилиальную архитектуру: врачи, услуги и цены могут отличаться по филиалам
- Ролевой доступ: супер-администратор и менеджеры отдельных филиалов

---

## 2. Django Applications

Каждый домен — отдельное Django-приложение в `apps/`:

| App | Ответственность |
|-----|----------------|
| `users` | Кастомная модель пользователя, роли, привязка к филиалу |
| `branches` | Филиалы: адрес, телефоны, часы работы, координаты |
| `doctors` | Врачи, специализации, фото; связь с филиалами через промежуточную таблицу |
| `services` | Услуги и категории; цена хранится в промежуточной таблице per-branch |
| `blog` | Статьи с CKEditor 5, категории, статусы draft/published |
| `promotions` | Акции: баннер, даты, привязка к филиалам |
| `appointments` | Заявки пациентов с Django-сигналом для будущего Telegram-бота |

---

## 3. Data Models

### users
```
User (AbstractUser)
  - role: choices [superadmin, branch_manager]
  - branch: FK → Branch (null для superadmin)
```

### branches
```
Branch
  - name: str
  - address: str
  - phone: str
  - email: str
  - working_hours: JSONField  # {"mon-fri": "9:00-20:00", "sat": "10:00-18:00"}
  - coordinates: JSONField    # {"lat": ..., "lng": ...}
  - is_active: bool
```

### doctors
```
Doctor
  - first_name, last_name, patronymic: str
  - photo: ImageField
  - bio: TextField (CKEditor 5)
  - specializations: M2M → Specialization

Specialization
  - name: str

DoctorBranch (промежуточная таблица)
  - doctor: FK → Doctor
  - branch: FK → Branch
  - schedule: JSONField  # расписание врача в конкретном филиале
  - is_active: bool
```

### services
```
ServiceCategory
  - name: str
  - slug: str
  - icon: ImageField

Service
  - name: str
  - slug: str
  - category: FK → ServiceCategory
  - description: TextField (CKEditor 5)
  - is_active: bool

BranchService (промежуточная таблица)
  - branch: FK → Branch
  - service: FK → Service
  - price: DecimalField
  - price_from: bool  # "от X рублей"
  - is_active: bool
```

### blog
```
BlogCategory
  - name: str
  - slug: str

BlogPost
  - title: str
  - slug: str
  - category: FK → BlogCategory
  - cover: ImageField
  - excerpt: TextField
  - content: CKEditor5Field
  - status: choices [draft, published]
  - published_at: DateTimeField
  - created_at: DateTimeField
```

### promotions
```
Promotion
  - title: str
  - description: TextField (CKEditor 5)
  - banner: ImageField
  - starts_at: DateField
  - ends_at: DateField (nullable)
  - branches: M2M → Branch
  - is_active: bool
```

### appointments
```
Appointment
  - patient_name: str
  - patient_phone: str
  - branch: FK → Branch
  - doctor: FK → Doctor (nullable)
  - service: FK → Service (nullable)
  - comment: TextField
  - status: choices [new, in_progress, done]
  - created_at: DateTimeField

# Сигнал: post_save → notify_telegram() — заглушка для будущего бота
```

---

## 4. API (Django Ninja)

Базовый префикс: `/api/v1/`

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/branches/` | Список активных филиалов |
| GET | `/branches/{id}/` | Детали филиала |
| GET | `/doctors/` | Список врачей (фильтр: `?branch_id=`) |
| GET | `/doctors/{id}/` | Детали врача |
| GET | `/services/` | Услуги с ценами (фильтр: `?branch_id=`, `?category=`) |
| GET | `/services/categories/` | Категории услуг |
| GET | `/blog/` | Опубликованные статьи |
| GET | `/blog/{slug}/` | Детали статьи |
| GET | `/promotions/` | Активные акции (фильтр: `?branch_id=`) |
| POST | `/appointments/` | Создать заявку (публичный) |

Все GET-эндпоинты публичны и доступны без аутентификации.
OpenAPI-документация: `/api/docs`

---

## 5. Admin Panel (django-jazzmin)

**Конфигурация Jazzmin:**
- Логотип и цвета клиники в `JAZZMIN_SETTINGS`
- Боковое меню сгруппировано: Филиалы → Врачи → Услуги → Блог → Акции → Заявки

**Ролевой доступ:**
- `superadmin`: полный доступ ко всем данным
- `branch_manager`: переопределение `get_queryset()` в каждом `ModelAdmin` — фильтрация по `request.user.branch`

**Rich text (CKEditor 5):**
- Поля `content`/`bio`/`description` в BlogPost, Doctor, Service, Promotion

**Заявки:**
- Статус переключается через `list_editable` прямо в списке
- Фильтр по филиалу и статусу в правой панели

---

## 6. Project Structure

```
alexa-backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── api.py              # регистрация всех Ninja-роутеров
├── apps/
│   ├── users/
│   ├── branches/
│   ├── doctors/
│   ├── services/
│   ├── blog/
│   ├── promotions/
│   └── appointments/
├── media/
├── static/
├── .env
├── .env.example
├── manage.py
├── requirements.txt
└── docker-compose.yml
```

---

## 7. Tech Stack

| Компонент | Библиотека / версия |
|-----------|-------------------|
| Фреймворк | Django 5.x |
| API | django-ninja |
| Admin UI | django-jazzmin |
| Rich text | django-ckeditor-5 |
| БД | PostgreSQL + psycopg2-binary |
| Изображения | Pillow |
| Env | python-decouple |
| CORS | django-cors-headers |
| Prod-сервер | gunicorn |

---

## 8. Telegram Integration Point

Модель `Appointment` содержит сигнал `post_save`, который вызывает `notify_telegram(appointment)`.
На данном этапе функция является заглушкой. При подключении Telegram-бота реализуется без изменения модели — только `notify_telegram()`.

---

## 9. Docker

`docker-compose.yml` включает два сервиса:
- `db` — PostgreSQL 16
- `web` — Django (gunicorn в prod, runserver в dev)

Структура аналогична `alexa-webapp/docker/`.
