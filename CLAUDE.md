# Alexa Backend — Developer Guide

## Проект
Django 5.1.4 backend для стоматологической клиники Alexa. Мультифилиальная система,
ролевой admin (superadmin / branch_manager), публичный REST API через Django Ninja.

## Быстрый старт
```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
# API docs: http://localhost:8000/api/v1/docs
# Admin:    http://localhost:8000/admin/
```

## Тесты
```bash
# Все тесты (--keepdb — БД test_alexa уже существует в Docker)
docker-compose exec web python manage.py test -v 2 --keepdb

# Тесты одного приложения
docker-compose exec web python manage.py test apps.doctors -v 2 --keepdb

# Или через Makefile:
make test
make test-app APP=doctors
```

## Стек
| Пакет | Версия | Назначение |
|---|---|---|
| Django | 5.1.4 | Основной фреймворк |
| django-ninja | 1.3 | REST API (FastAPI-style схемы) |
| django-jazzmin | 3.0 | Кастомный UI для /admin/ |
| django-ckeditor-5 | 0.2 | Rich-text поля |
| Pillow | 10.4 | ImageField / обработка фото |
| postgresql | 16 | БД |
| python-decouple | 3.8 | Конфигурация через .env |

## Структура проекта
```
apps/
  users/        # Кастомная User модель — Role, FK на Branch
  branches/     # Филиалы клиники — ГОТОВО
  doctors/      # Врачи, специализации, DoctorBranch — ГОТОВО
  services/     # Услуги, категории, BranchService — models only
  blog/         # BlogPost, BlogCategory — models only
  promotions/   # Акции с M2M на Branch, фильтрация по датам — models only
  appointments/ # Запись на приём + Telegram signal stub — models only
config/
  settings/base.py  # Все настройки, INSTALLED_APPS
  api.py            # Центральный роутер — сюда добавлять новые роутеры
  urls.py           # URL routing
docs/superpowers/plans/2026-06-23-alexa-backend.md  # Полный план (9 задач)
```

Все приложения уже зарегистрированы в `INSTALLED_APPS` (base.py) — повторно не добавлять.

---

## Паттерн Django-приложения (повторять для services, blog, promotions, appointments)

### models.py
- Russian verbose_name на ВСЕХ полях и в Meta
- Cross-app FK через строку: `'branches.Branch'` (не import, чтобы избежать circular)
- Rich text: `CKEditor5Field(blank=True, config_name='default')`
- Images: `ImageField(upload_to='appname/')`
- Всегда определять `__str__` и `ordering` в Meta

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

class MyModel(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Модель'
        verbose_name_plural = 'Модели'
        ordering = ['name']

    def __str__(self):
        return self.name
```

### admin.py
- `BranchFilterMixin` из `apps.users.mixins` — для всех моделей с привязкой к филиалу
- `branch_filter_field` — ORM-путь от модели до Branch:
  - Прямой FK: `'branch'` (значение по умолчанию, можно не переопределять)
  - Через таблицу-посредник: `'doctorbranch__branch'`
  - Нет привязки к филиалу (глобальные справочники): BranchFilterMixin не нужен

```python
from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'branch'      # переопределить если не прямой FK
    list_display  = ['name', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']
    list_filter   = ['is_active']
```

### schemas.py

```python
from ninja import Schema
from typing import Optional

class MyModelSchema(Schema):
    id: int
    name: str
    is_active: bool

    # Для ImageField — resolver возвращает URL строкой
    photo: Optional[str] = None

    @staticmethod
    def resolve_photo(obj):
        return obj.photo.url if obj.photo else None
```

### api.py

```python
from ninja import Router
from django.shortcuts import get_object_or_404
from typing import Optional
from .models import MyModel
from .schemas import MyModelSchema

router = Router(tags=['MyApp'])

@router.get('/', response=list[MyModelSchema])
def list_items(request):
    return MyModel.objects.filter(is_active=True)

@router.get('/{item_id}/', response=MyModelSchema)
def get_item(request, item_id: int):
    return get_object_or_404(MyModel, id=item_id, is_active=True)
```

Затем зарегистрировать в `config/api.py`:
```python
from apps.myapp.api import router as myapp_router
api.add_router("/myapp/", myapp_router)
```

### tests.py

```python
from django.test import TestCase
from apps.branches.models import Branch
from .models import MyModel

class MyModelTest(TestCase):
    def setUp(self):
        self.obj = MyModel.objects.create(name='Test')

    def test_str_representation(self):
        self.assertEqual(str(self.obj), 'Test')


class MyAPITest(TestCase):
    def setUp(self):
        self.obj     = MyModel.objects.create(name='Active',   is_active=True)
        self.inactive = MyModel.objects.create(name='Inactive', is_active=False)

    def test_list_returns_only_active(self):
        response = self.client.get('/api/v1/myapp/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_detail_ok(self):
        response = self.client.get(f'/api/v1/myapp/{self.obj.id}/')
        self.assertEqual(response.status_code, 200)

    def test_inactive_returns_404(self):
        response = self.client.get(f'/api/v1/myapp/{self.inactive.id}/')
        self.assertEqual(response.status_code, 404)
```

### Миграции
```bash
# Использовать короткое имя (services), не apps.services
docker-compose exec web python manage.py makemigrations services
docker-compose exec web python manage.py migrate
# Или: make migrate APP=services
```

---

## Ключевые утилиты

### BranchFilterMixin (apps/users/mixins.py)
Ограничивает queryset в admin по филиалу пользователя:
- `superadmin` → видит всё
- `branch_manager` → видит только записи своего филиала
- Если связь не прямой FK, указать путь: `branch_filter_field = 'doctorbranch__branch'`

### User модель (apps/users/models.py)
```python
User.Role.SUPERADMIN      # 'superadmin'
User.Role.BRANCH_MANAGER  # 'branch_manager'
user.branch               # FK → Branch (None для superadmin)
user.role                 # строка роли
```

---

## Соглашения API
- Base URL: `/api/v1/`
- Публичные endpoints без аутентификации (информация о клинике публична)
- Все list-endpoints фильтруют `is_active=True`
- Branch-фильтрация: опциональный `?branch_id=` там, где уместно
- Inactive записи → 404 на detail endpoint
- При JOIN через M2M или FK использовать `.distinct()` против дублей
- `prefetch_related()` для M2M, `select_related()` для FK — избегать N+1

## INSTALLED_APPS (не менять порядок)
`jazzmin` → `django.contrib.*` → `ninja, corsheaders, django_ckeditor_5` → `apps.*`
jazzmin обязан идти перед `django.contrib.admin`.

## Переменные окружения (.env)
```
SECRET_KEY, DEBUG, ALLOWED_HOSTS
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
CORS_ALLOWED_ORIGINS   # default: http://localhost:3000
```
