# Alexa Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать Django + Ninja backend для стоматологии «Алекса» с мультифилиальной архитектурой, ролевой admin-панелью на jazzmin и публичным REST API для Next.js-фронтенда.

**Architecture:** Feature-based Django apps (users, branches, doctors, services, blog, promotions, appointments). Каждый app содержит модели, admin, ninja-роутер и схемы. AUTH_USER_MODEL установлен до первой миграции.

**Tech Stack:** Django 5.1, django-ninja 1.3, django-jazzmin 3.0, django-ckeditor-5 0.2, PostgreSQL 16, psycopg2-binary, Pillow, python-decouple, django-cors-headers, gunicorn.

## Global Constraints

- Python 3.12
- Django 5.1.4 — не ниже
- AUTH_USER_MODEL = 'users.User' — задаётся в base.py до любых миграций
- Все FK на Branch используют строковые ссылки `'branches.Branch'`
- Все API-эндпоинты публичны (без аутентификации), кроме POST /appointments/ который тоже публичный
- Медиафайлы хранятся в `media/` в корне проекта
- CORS разрешён для `http://localhost:3000` (фронтенд)
- API prefix: `/api/v1/`

---

## File Map

```
alexa-backend/
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── requirements.txt
├── config/
│   ├── __init__.py
│   ├── api.py
│   ├── urls.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       └── prod.py
└── apps/
    ├── users/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── mixins.py       # BranchFilterMixin для всех ModelAdmin
    │   ├── models.py
    │   ├── migrations/__init__.py
    │   └── tests.py
    ├── branches/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── api.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── migrations/__init__.py
    │   └── tests.py
    ├── doctors/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── api.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── migrations/__init__.py
    │   └── tests.py
    ├── services/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── api.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── migrations/__init__.py
    │   └── tests.py
    ├── blog/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── api.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── migrations/__init__.py
    │   └── tests.py
    ├── promotions/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── api.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── migrations/__init__.py
    │   └── tests.py
    └── appointments/
        ├── __init__.py
        ├── admin.py
        ├── api.py
        ├── apps.py
        ├── models.py
        ├── schemas.py
        ├── signals.py
        ├── migrations/__init__.py
        └── tests.py
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `config/__init__.py`
- Create: `config/settings/__init__.py`
- Create: `config/settings/base.py`
- Create: `config/settings/dev.py`
- Create: `config/settings/prod.py`
- Create: `config/urls.py`
- Create: `config/api.py`
- Modify: `manage.py`

**Interfaces:**
- Produces: рабочее Django-приложение на PostgreSQL, `python manage.py check` проходит без ошибок

- [ ] **Step 1: Создать структуру директорий**

```bash
mkdir -p apps config/settings media static
touch config/__init__.py config/settings/__init__.py
touch apps/__init__.py
```

- [ ] **Step 2: Создать `requirements.txt`**

```
Django==5.1.4
django-ninja==1.3.0
django-jazzmin==3.0.1
django-ckeditor-5==0.2.15
psycopg2-binary==2.9.10
Pillow==10.4.0
python-decouple==3.8
django-cors-headers==4.6.0
gunicorn==23.0.0
```

- [ ] **Step 3: Создать виртуальное окружение и установить зависимости**

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Создать Django-проект**

```bash
django-admin startproject config .
```

Это создаст `config/wsgi.py`, `config/asgi.py` и перезапишет `config/settings.py`. Удали стандартный `config/settings.py`:

```bash
rm config/settings.py
```

- [ ] **Step 5: Написать `config/settings/base.py`**

```python
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'ninja',
    'corsheaders',
    'django_ckeditor_5',
]

LOCAL_APPS = [
    'apps.users',
    'apps.branches',
    'apps.doctors',
    'apps.services',
    'apps.blog',
    'apps.promotions',
    'apps.appointments',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='alexa'),
        'USER': config('DB_USER', default='alexa'),
        'PASSWORD': config('DB_PASSWORD', default='alexa'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': [
                'heading', '|',
                'bold', 'italic', 'underline', '|',
                'link', '|',
                'bulletedList', 'numberedList', '|',
                'blockQuote', '|',
                'imageUpload', '|',
                'undo', 'redo',
            ],
        },
    }
}

CKEDITOR_5_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
```

- [ ] **Step 6: Написать `config/settings/dev.py`**

```python
from .base import *

DEBUG = True

DATABASES['default']['HOST'] = config('DB_HOST', default='localhost')
```

- [ ] **Step 7: Написать `config/settings/prod.py`**

```python
from .base import *

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

- [ ] **Step 8: Написать `config/urls.py`**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 9: Написать `config/api.py`**

```python
from ninja import NinjaAPI

api = NinjaAPI(
    title="Alexa Dental API",
    version="1.0.0",
    docs_url="/docs",
)
```

Роутеры будут добавлены в каждом последующем task'е.

- [ ] **Step 10: Изменить `manage.py`**

Найди строку `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')` и замени на:

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
```

То же самое в `config/wsgi.py` и `config/asgi.py`.

- [ ] **Step 11: Создать `.env`**

```bash
cat > .env << 'EOF'
SECRET_KEY=django-insecure-change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=alexa
DB_USER=alexa
DB_PASSWORD=alexa
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000
EOF
```

- [ ] **Step 12: Создать `.env.example`**

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=alexa
DB_USER=alexa
DB_PASSWORD=alexa
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

- [ ] **Step 13: Создать `.gitignore`**

```
*.pyc
__pycache__/
*.pyo
.Python
venv/
.env
*.egg-info/
media/
staticfiles/
.DS_Store
*.sqlite3
```

- [ ] **Step 14: Создать `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

- [ ] **Step 15: Создать `docker-compose.yml`**

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

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    env_file:
      - .env
    environment:
      DB_HOST: db

volumes:
  postgres_data:
```

- [ ] **Step 16: Запустить PostgreSQL и проверить конфигурацию**

Запусти только базу данных:
```bash
docker-compose up -d db
```

Затем проверь Django:
```bash
python manage.py check
```

Ожидаемый вывод: `System check identified no issues (0 silenced).`

- [ ] **Step 17: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding — Django 5.1, Ninja, Jazzmin, Docker"
```

---

### Task 2: Users App (Custom User Model)

**Важно:** этот app создаётся до первой миграции, иначе AUTH_USER_MODEL не будет работать.

**Files:**
- Create: `apps/users/__init__.py`
- Create: `apps/users/apps.py`
- Create: `apps/users/models.py`
- Create: `apps/users/mixins.py`
- Create: `apps/users/admin.py`
- Create: `apps/users/migrations/__init__.py`
- Create: `apps/users/tests.py`

**Interfaces:**
- Produces: `User` model с полями `role` и `branch`; `BranchFilterMixin` для использования в admin других apps

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/users/migrations
touch apps/users/__init__.py apps/users/migrations/__init__.py
```

- [ ] **Step 2: Написать failing test**

```python
# apps/users/tests.py
from django.test import TestCase
from apps.users.models import User


class UserModelTest(TestCase):
    def test_create_superadmin(self):
        user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role=User.Role.SUPERADMIN,
        )
        self.assertEqual(user.role, User.Role.SUPERADMIN)
        self.assertIsNone(user.branch)

    def test_create_branch_manager_without_branch(self):
        user = User.objects.create_user(
            username='manager',
            password='testpass123',
            role=User.Role.BRANCH_MANAGER,
        )
        self.assertEqual(user.role, User.Role.BRANCH_MANAGER)
        self.assertIsNone(user.branch)

    def test_str_representation(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Иван',
            last_name='Иванов',
        )
        self.assertEqual(str(user), 'Иван Иванов')
```

- [ ] **Step 3: Убедиться что тест падает**

```bash
python manage.py test apps.users.tests -v 2
```

Ожидаемый вывод: `ImportError: cannot import name 'User' from 'apps.users.models'`

- [ ] **Step 4: Написать `apps/users/apps.py`**

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Пользователи'
```

- [ ] **Step 5: Написать `apps/users/models.py`**

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Супер-администратор'
        BRANCH_MANAGER = 'branch_manager', 'Менеджер филиала'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BRANCH_MANAGER,
        verbose_name='Роль',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managers',
        verbose_name='Филиал',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.get_full_name() or self.username
```

- [ ] **Step 6: Написать `apps/users/mixins.py`**

```python
class BranchFilterMixin:
    """
    Mixin for ModelAdmin to restrict branch managers to their own branch.
    Set branch_filter_field to the queryset filter path, e.g. 'branch' or 'doctorbranch__branch'.
    """
    branch_filter_field = 'branch'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(**{self.branch_filter_field: branch})
        return qs.none()
```

- [ ] **Step 7: Написать `apps/users/admin.py`**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'branch', 'is_active']
    list_filter = ['role', 'branch', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Роль и доступ', {'fields': ('role', 'branch')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Роль и доступ', {'fields': ('role', 'branch')}),
    )
```

- [ ] **Step 8: Создать и применить миграции**

```bash
python manage.py makemigrations users
python manage.py migrate
```

Ожидаемый вывод последней строки: `Applying users.0001_initial... OK`

- [ ] **Step 9: Запустить тесты**

```bash
python manage.py test apps.users.tests -v 2
```

Ожидаемый вывод: `Ran 3 tests in ...s OK`

- [ ] **Step 10: Commit**

```bash
git add apps/users/ config/settings/base.py
git commit -m "feat: custom User model with role and branch FK"
```

---

### Task 3: Branches App

**Files:**
- Create: `apps/branches/__init__.py`
- Create: `apps/branches/apps.py`
- Create: `apps/branches/models.py`
- Create: `apps/branches/admin.py`
- Create: `apps/branches/schemas.py`
- Create: `apps/branches/api.py`
- Create: `apps/branches/migrations/__init__.py`
- Create: `apps/branches/tests.py`
- Modify: `config/api.py`

**Interfaces:**
- Consumes: `BranchFilterMixin` из `apps.users.mixins`
- Produces: `Branch` model; `GET /api/v1/branches/` и `GET /api/v1/branches/{id}/`

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/branches/migrations
touch apps/branches/__init__.py apps/branches/migrations/__init__.py
```

- [ ] **Step 2: Написать failing tests**

```python
# apps/branches/tests.py
from django.test import TestCase, Client
from apps.branches.models import Branch


class BranchModelTest(TestCase):
    def test_create_branch(self):
        branch = Branch.objects.create(
            name='Центральный',
            address='ул. Ленина, 1',
            phone='+7-999-000-0001',
            email='main@alexa.ru',
        )
        self.assertEqual(str(branch), 'Центральный')
        self.assertTrue(branch.is_active)

    def test_working_hours_defaults_to_empty_dict(self):
        branch = Branch.objects.create(
            name='Северный',
            address='ул. Северная, 5',
            phone='+7-999-000-0002',
            email='north@alexa.ru',
        )
        self.assertEqual(branch.working_hours, {})
        self.assertEqual(branch.coordinates, {})


class BranchAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный',
            address='ул. Ленина, 1',
            phone='+7-999-000-0001',
            email='main@alexa.ru',
            is_active=True,
        )
        Branch.objects.create(
            name='Закрытый',
            address='ул. Старая, 9',
            phone='+7-999-000-0009',
            email='old@alexa.ru',
            is_active=False,
        )

    def test_list_branches_returns_only_active(self):
        response = self.client.get('/api/v1/branches/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Центральный')

    def test_get_branch_detail(self):
        response = self.client.get(f'/api/v1/branches/{self.branch.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Центральный')

    def test_get_inactive_branch_returns_404(self):
        inactive = Branch.objects.get(name='Закрытый')
        response = self.client.get(f'/api/v1/branches/{inactive.id}/')
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 3: Убедиться что тесты падают**

```bash
python manage.py test apps.branches.tests -v 2
```

Ожидаемый вывод: `ImportError` или `ModuleNotFoundError`

- [ ] **Step 4: Написать `apps/branches/apps.py`**

```python
from django.apps import AppConfig


class BranchesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.branches'
    verbose_name = 'Филиалы'
```

- [ ] **Step 5: Написать `apps/branches/models.py`**

```python
from django.db import models


class Branch(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    address = models.CharField(max_length=500, verbose_name='Адрес')
    phone = models.CharField(max_length=30, verbose_name='Телефон')
    email = models.EmailField(verbose_name='Email')
    working_hours = models.JSONField(default=dict, blank=True, verbose_name='Часы работы')
    coordinates = models.JSONField(default=dict, blank=True, verbose_name='Координаты')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Филиал'
        verbose_name_plural = 'Филиалы'
        ordering = ['name']

    def __str__(self):
        return self.name
```

- [ ] **Step 6: Написать `apps/branches/schemas.py`**

```python
from ninja import Schema


class BranchSchema(Schema):
    id: int
    name: str
    address: str
    phone: str
    email: str
    working_hours: dict
    coordinates: dict
    is_active: bool
```

- [ ] **Step 7: Написать `apps/branches/api.py`**

```python
from ninja import Router
from django.shortcuts import get_object_or_404
from .models import Branch
from .schemas import BranchSchema

router = Router(tags=['Branches'])


@router.get('/', response=list[BranchSchema])
def list_branches(request):
    return Branch.objects.filter(is_active=True)


@router.get('/{branch_id}/', response=BranchSchema)
def get_branch(request, branch_id: int):
    return get_object_or_404(Branch, id=branch_id, is_active=True)
```

- [ ] **Step 8: Написать `apps/branches/admin.py`**

```python
from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Branch


@admin.register(Branch)
class BranchAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'id'
    list_display = ['name', 'address', 'phone', 'email', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'address']
    list_filter = ['is_active']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(id=branch.id)
        return qs.none()
```

- [ ] **Step 9: Зарегистрировать роутер в `config/api.py`**

```python
from ninja import NinjaAPI
from apps.branches.api import router as branches_router

api = NinjaAPI(
    title="Alexa Dental API",
    version="1.0.0",
    docs_url="/docs",
)

api.add_router("/branches/", branches_router)
```

- [ ] **Step 10: Создать и применить миграции**

```bash
python manage.py makemigrations branches
python manage.py migrate
```

Ожидаемый вывод: `Applying branches.0001_initial... OK`

- [ ] **Step 11: Запустить тесты**

```bash
python manage.py test apps.branches.tests apps.users.tests -v 2
```

Ожидаемый вывод: `Ran 5 tests in ...s OK`

- [ ] **Step 12: Commit**

```bash
git add apps/branches/ config/api.py
git commit -m "feat: branches app — model, admin, API endpoints"
```

---

### Task 4: Doctors App

**Files:**
- Create: `apps/doctors/__init__.py`
- Create: `apps/doctors/apps.py`
- Create: `apps/doctors/models.py`
- Create: `apps/doctors/admin.py`
- Create: `apps/doctors/schemas.py`
- Create: `apps/doctors/api.py`
- Create: `apps/doctors/migrations/__init__.py`
- Create: `apps/doctors/tests.py`
- Modify: `config/api.py`

**Interfaces:**
- Consumes: `Branch` из `apps.branches.models`; `BranchFilterMixin` из `apps.users.mixins`
- Produces: `Doctor`, `Specialization`, `DoctorBranch` models; `GET /api/v1/doctors/` (фильтр `?branch_id=`); `GET /api/v1/doctors/{id}/`

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/doctors/migrations
touch apps/doctors/__init__.py apps/doctors/migrations/__init__.py
```

- [ ] **Step 2: Написать failing tests**

```python
# apps/doctors/tests.py
from django.test import TestCase, Client
from apps.branches.models import Branch
from apps.doctors.models import Doctor, Specialization, DoctorBranch


class DoctorModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        self.spec = Specialization.objects.create(name='Терапевт')
        self.doctor = Doctor.objects.create(
            first_name='Анна',
            last_name='Петрова',
            patronymic='Сергеевна',
        )

    def test_str_representation(self):
        self.assertEqual(str(self.doctor), 'Петрова Анна Сергеевна')

    def test_doctor_branch_relationship(self):
        DoctorBranch.objects.create(doctor=self.doctor, branch=self.branch)
        self.assertIn(self.branch, self.doctor.branches.all())

    def test_specialization_str(self):
        self.assertEqual(str(self.spec), 'Терапевт')


class DoctorAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch1 = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        self.branch2 = Branch.objects.create(
            name='Северный', address='ул. Северная, 5',
            phone='+7-999-000-0002', email='north@alexa.ru',
        )
        self.doctor1 = Doctor.objects.create(
            first_name='Анна', last_name='Петрова', patronymic='Сергеевна',
        )
        self.doctor2 = Doctor.objects.create(
            first_name='Иван', last_name='Сидоров', patronymic='Петрович',
        )
        DoctorBranch.objects.create(doctor=self.doctor1, branch=self.branch1, is_active=True)
        DoctorBranch.objects.create(doctor=self.doctor2, branch=self.branch2, is_active=True)

    def test_list_all_doctors(self):
        response = self.client.get('/api/v1/doctors/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_filter_doctors_by_branch(self):
        response = self.client.get(f'/api/v1/doctors/?branch_id={self.branch1.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['last_name'], 'Петрова')

    def test_get_doctor_detail(self):
        response = self.client.get(f'/api/v1/doctors/{self.doctor1.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['first_name'], 'Анна')
```

- [ ] **Step 3: Убедиться что тесты падают**

```bash
python manage.py test apps.doctors.tests -v 2
```

Ожидаемый вывод: `ImportError`

- [ ] **Step 4: Написать `apps/doctors/apps.py`**

```python
from django.apps import AppConfig


class DoctorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.doctors'
    verbose_name = 'Врачи'
```

- [ ] **Step 5: Написать `apps/doctors/models.py`**

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class Specialization(models.Model):
    name = models.CharField(max_length=255, verbose_name='Специализация')

    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(models.Model):
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    patronymic = models.CharField(max_length=100, blank=True, verbose_name='Отчество')
    photo = models.ImageField(upload_to='doctors/', blank=True, verbose_name='Фото')
    bio = CKEditor5Field('bio', config_name='default', blank=True, verbose_name='Биография')
    specializations = models.ManyToManyField(
        Specialization,
        blank=True,
        related_name='doctors',
        verbose_name='Специализации',
    )
    branches = models.ManyToManyField(
        'branches.Branch',
        through='DoctorBranch',
        related_name='doctors',
        verbose_name='Филиалы',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        parts = [self.last_name, self.first_name]
        if self.patronymic:
            parts.append(self.patronymic)
        return ' '.join(parts)


class DoctorBranch(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Врач')
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE, verbose_name='Филиал'
    )
    schedule = models.JSONField(default=dict, blank=True, verbose_name='Расписание')
    is_active = models.BooleanField(default=True, verbose_name='Активен в филиале')

    class Meta:
        unique_together = ('doctor', 'branch')
        verbose_name = 'Врач в филиале'
        verbose_name_plural = 'Врачи в филиалах'
```

- [ ] **Step 6: Написать `apps/doctors/schemas.py`**

```python
from ninja import Schema
from typing import Optional


class SpecializationSchema(Schema):
    id: int
    name: str


class DoctorSchema(Schema):
    id: int
    first_name: str
    last_name: str
    patronymic: str
    photo: Optional[str] = None
    bio: str
    is_active: bool
    specializations: list[SpecializationSchema] = []

    @staticmethod
    def resolve_photo(obj):
        if obj.photo:
            return obj.photo.url
        return None
```

- [ ] **Step 7: Написать `apps/doctors/api.py`**

```python
from ninja import Router
from typing import Optional
from django.shortcuts import get_object_or_404
from .models import Doctor
from .schemas import DoctorSchema

router = Router(tags=['Doctors'])


@router.get('/', response=list[DoctorSchema])
def list_doctors(request, branch_id: Optional[int] = None):
    qs = Doctor.objects.filter(is_active=True).prefetch_related('specializations')
    if branch_id:
        qs = qs.filter(doctorbranch__branch_id=branch_id, doctorbranch__is_active=True)
    return qs


@router.get('/{doctor_id}/', response=DoctorSchema)
def get_doctor(request, doctor_id: int):
    return get_object_or_404(Doctor, id=doctor_id, is_active=True)
```

- [ ] **Step 8: Написать `apps/doctors/admin.py`**

```python
from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Doctor, Specialization, DoctorBranch


class DoctorBranchInline(admin.TabularInline):
    model = DoctorBranch
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'doctorbranch__branch'
    list_display = ['last_name', 'first_name', 'patronymic', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active', 'specializations']
    search_fields = ['last_name', 'first_name']
    filter_horizontal = ['specializations']
    inlines = [DoctorBranchInline]


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
```

- [ ] **Step 9: Добавить роутер в `config/api.py`**

```python
from ninja import NinjaAPI
from apps.branches.api import router as branches_router
from apps.doctors.api import router as doctors_router

api = NinjaAPI(
    title="Alexa Dental API",
    version="1.0.0",
    docs_url="/docs",
)

api.add_router("/branches/", branches_router)
api.add_router("/doctors/", doctors_router)
```

- [ ] **Step 10: Создать и применить миграции**

```bash
python manage.py makemigrations doctors
python manage.py migrate
```

Ожидаемый вывод: `Applying doctors.0001_initial... OK`

- [ ] **Step 11: Запустить тесты**

```bash
python manage.py test apps.doctors.tests apps.branches.tests apps.users.tests -v 2
```

Ожидаемый вывод: `Ran 9 tests in ...s OK`

- [ ] **Step 12: Commit**

```bash
git add apps/doctors/ config/api.py
git commit -m "feat: doctors app — Specialization, Doctor, DoctorBranch, API"
```

---

### Task 5: Services App

**Files:**
- Create: `apps/services/__init__.py`
- Create: `apps/services/apps.py`
- Create: `apps/services/models.py`
- Create: `apps/services/admin.py`
- Create: `apps/services/schemas.py`
- Create: `apps/services/api.py`
- Create: `apps/services/migrations/__init__.py`
- Create: `apps/services/tests.py`
- Modify: `config/api.py`

**Interfaces:**
- Consumes: `Branch` из `apps.branches.models`; `BranchFilterMixin` из `apps.users.mixins`
- Produces: `ServiceCategory`, `Service`, `BranchService` models; `GET /api/v1/services/` (фильтр `?branch_id=`, `?category=`); `GET /api/v1/services/categories/`

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/services/migrations
touch apps/services/__init__.py apps/services/migrations/__init__.py
```

- [ ] **Step 2: Написать failing tests**

```python
# apps/services/tests.py
from django.test import TestCase, Client
from decimal import Decimal
from apps.branches.models import Branch
from apps.services.models import ServiceCategory, Service, BranchService


class ServiceModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        self.category = ServiceCategory.objects.create(name='Терапия', slug='therapy')
        self.service = Service.objects.create(
            name='Лечение кариеса', slug='caries', category=self.category,
        )

    def test_service_str(self):
        self.assertEqual(str(self.service), 'Лечение кариеса')

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Терапия')

    def test_branch_service_price(self):
        bs = BranchService.objects.create(
            branch=self.branch, service=self.service,
            price=Decimal('3500.00'), price_from=False,
        )
        self.assertEqual(bs.price, Decimal('3500.00'))
        self.assertFalse(bs.price_from)


class ServiceAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        self.category = ServiceCategory.objects.create(name='Терапия', slug='therapy')
        self.service = Service.objects.create(
            name='Лечение кариеса', slug='caries', category=self.category, is_active=True,
        )
        BranchService.objects.create(
            branch=self.branch, service=self.service,
            price=Decimal('3500.00'), is_active=True,
        )

    def test_list_categories(self):
        response = self.client.get('/api/v1/services/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_list_services_filtered_by_branch(self):
        response = self.client.get(f'/api/v1/services/?branch_id={self.branch.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['price'], '3500.00')
```

- [ ] **Step 3: Убедиться что тесты падают**

```bash
python manage.py test apps.services.tests -v 2
```

Ожидаемый вывод: `ImportError`

- [ ] **Step 4: Написать `apps/services/apps.py`**

```python
from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.services'
    verbose_name = 'Услуги'
```

- [ ] **Step 5: Написать `apps/services/models.py`**

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class ServiceCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    icon = models.ImageField(upload_to='service_categories/', blank=True, verbose_name='Иконка')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Категория услуг'
        verbose_name_plural = 'Категории услуг'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT,
        related_name='services', verbose_name='Категория',
    )
    description = CKEditor5Field('description', config_name='default', blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class BranchService(models.Model):
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE,
        related_name='branch_services', verbose_name='Филиал',
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE,
        related_name='branch_services', verbose_name='Услуга',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_from = models.BooleanField(default=False, verbose_name='От (цена примерная)')
    is_active = models.BooleanField(default=True, verbose_name='Активна в филиале')

    class Meta:
        unique_together = ('branch', 'service')
        verbose_name = 'Услуга в филиале'
        verbose_name_plural = 'Услуги в филиалах'
```

- [ ] **Step 6: Написать `apps/services/schemas.py`**

```python
from ninja import Schema
from decimal import Decimal
from typing import Optional


class ServiceCategorySchema(Schema):
    id: int
    name: str
    slug: str
    icon: Optional[str] = None

    @staticmethod
    def resolve_icon(obj):
        return obj.icon.url if obj.icon else None


class ServiceWithPriceSchema(Schema):
    id: int
    name: str
    slug: str
    category_id: int
    price: Decimal
    price_from: bool
```

- [ ] **Step 7: Написать `apps/services/api.py`**

```python
from ninja import Router
from typing import Optional
from .models import ServiceCategory, BranchService
from .schemas import ServiceCategorySchema, ServiceWithPriceSchema

router = Router(tags=['Services'])


@router.get('/categories/', response=list[ServiceCategorySchema])
def list_categories(request):
    return ServiceCategory.objects.all()


@router.get('/', response=list[ServiceWithPriceSchema])
def list_services(request, branch_id: Optional[int] = None, category: Optional[str] = None):
    qs = BranchService.objects.filter(
        is_active=True, service__is_active=True,
    ).select_related('service', 'service__category')
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if category:
        qs = qs.filter(service__category__slug=category)

    return [
        ServiceWithPriceSchema(
            id=bs.service.id,
            name=bs.service.name,
            slug=bs.service.slug,
            category_id=bs.service.category_id,
            price=bs.price,
            price_from=bs.price_from,
        )
        for bs in qs
    ]
```

- [ ] **Step 8: Написать `apps/services/admin.py`**

```python
from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import ServiceCategory, Service, BranchService


class BranchServiceInline(BranchFilterMixin, admin.TabularInline):
    model = BranchService
    extra = 1
    branch_filter_field = 'branch'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(branch=branch)
        return qs.none()


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_editable = ['is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BranchServiceInline]
```

- [ ] **Step 9: Добавить роутер в `config/api.py`**

Добавь в существующий `config/api.py`:

```python
from apps.services.api import router as services_router
api.add_router("/services/", services_router)
```

- [ ] **Step 10: Создать и применить миграции**

```bash
python manage.py makemigrations services
python manage.py migrate
```

Ожидаемый вывод: `Applying services.0001_initial... OK`

- [ ] **Step 11: Запустить тесты**

```bash
python manage.py test apps.services.tests -v 2
```

Ожидаемый вывод: `Ran 4 tests in ...s OK`

- [ ] **Step 12: Commit**

```bash
git add apps/services/ config/api.py
git commit -m "feat: services app — ServiceCategory, Service, BranchService, API"
```

---

### Task 6: Blog App

**Files:**
- Create: `apps/blog/__init__.py`
- Create: `apps/blog/apps.py`
- Create: `apps/blog/models.py`
- Create: `apps/blog/admin.py`
- Create: `apps/blog/schemas.py`
- Create: `apps/blog/api.py`
- Create: `apps/blog/migrations/__init__.py`
- Create: `apps/blog/tests.py`
- Modify: `config/api.py`

**Interfaces:**
- Produces: `BlogCategory`, `BlogPost` models (CKEditor5Field на `content`); `GET /api/v1/blog/`; `GET /api/v1/blog/{slug}/`

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/blog/migrations
touch apps/blog/__init__.py apps/blog/migrations/__init__.py
```

- [ ] **Step 2: Написать failing tests**

```python
# apps/blog/tests.py
from django.test import TestCase, Client
from django.utils import timezone
from apps.blog.models import BlogCategory, BlogPost


class BlogModelTest(TestCase):
    def setUp(self):
        self.category = BlogCategory.objects.create(name='Новости', slug='news')
        self.post = BlogPost.objects.create(
            title='Тест',
            slug='test',
            category=self.category,
            excerpt='Краткое описание',
            content='<p>Полный текст</p>',
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_post_str(self):
        self.assertEqual(str(self.post), 'Тест')

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Новости')


class BlogAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        category = BlogCategory.objects.create(name='Новости', slug='news')
        self.published = BlogPost.objects.create(
            title='Опубликовано', slug='published', category=category,
            excerpt='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.PUBLISHED, published_at=timezone.now(),
        )
        BlogPost.objects.create(
            title='Черновик', slug='draft', category=category,
            excerpt='Анонс', content='<p>Текст</p>',
            status=BlogPost.Status.DRAFT,
        )

    def test_list_returns_only_published(self):
        response = self.client.get('/api/v1/blog/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['title'], 'Опубликовано')

    def test_get_post_by_slug(self):
        response = self.client.get('/api/v1/blog/published/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slug'], 'published')

    def test_get_draft_returns_404(self):
        response = self.client.get('/api/v1/blog/draft/')
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 3: Убедиться что тесты падают**

```bash
python manage.py test apps.blog.tests -v 2
```

Ожидаемый вывод: `ImportError`

- [ ] **Step 4: Написать `apps/blog/apps.py`**

```python
from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog'
    verbose_name = 'Блог'
```

- [ ] **Step 5: Написать `apps/blog/models.py`**

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class BlogCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Slug')

    class Meta:
        verbose_name = 'Категория блога'
        verbose_name_plural = 'Категории блога'

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликовано'

    title = models.CharField(max_length=500, verbose_name='Заголовок')
    slug = models.SlugField(unique=True, verbose_name='Slug')
    category = models.ForeignKey(
        BlogCategory, on_delete=models.PROTECT,
        related_name='posts', verbose_name='Категория',
    )
    cover = models.ImageField(upload_to='blog/', blank=True, verbose_name='Обложка')
    excerpt = models.TextField(verbose_name='Краткое описание')
    content = CKEditor5Field('content', config_name='default', verbose_name='Контент')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, verbose_name='Статус',
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата публикации')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']

    def __str__(self):
        return self.title
```

- [ ] **Step 6: Написать `apps/blog/schemas.py`**

```python
from ninja import Schema
from datetime import datetime
from typing import Optional


class BlogCategorySchema(Schema):
    id: int
    name: str
    slug: str


class BlogPostListSchema(Schema):
    id: int
    title: str
    slug: str
    category: BlogCategorySchema
    cover: Optional[str] = None
    excerpt: str
    published_at: Optional[datetime] = None

    @staticmethod
    def resolve_cover(obj):
        return obj.cover.url if obj.cover else None


class BlogPostDetailSchema(BlogPostListSchema):
    content: str
```

- [ ] **Step 7: Написать `apps/blog/api.py`**

```python
from ninja import Router
from django.shortcuts import get_object_or_404
from .models import BlogPost
from .schemas import BlogPostListSchema, BlogPostDetailSchema

router = Router(tags=['Blog'])


@router.get('/', response=list[BlogPostListSchema])
def list_posts(request):
    return BlogPost.objects.filter(
        status=BlogPost.Status.PUBLISHED
    ).select_related('category')


@router.get('/{slug}/', response=BlogPostDetailSchema)
def get_post(request, slug: str):
    return get_object_or_404(BlogPost, slug=slug, status=BlogPost.Status.PUBLISHED)
```

- [ ] **Step 8: Написать `apps/blog/admin.py`**

```python
from django.contrib import admin
from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'published_at']
    list_editable = ['status']
    list_filter = ['status', 'category']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    readonly_fields = ['created_at']
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'status')}),
        ('Контент', {'fields': ('cover', 'excerpt', 'content')}),
        ('Даты', {'fields': ('published_at', 'created_at')}),
    )
```

- [ ] **Step 9: Добавить роутер в `config/api.py`**

Добавь в существующий `config/api.py`:

```python
from apps.blog.api import router as blog_router
api.add_router("/blog/", blog_router)
```

- [ ] **Step 10: Создать и применить миграции**

```bash
python manage.py makemigrations blog
python manage.py migrate
```

Ожидаемый вывод: `Applying blog.0001_initial... OK`

- [ ] **Step 11: Запустить тесты**

```bash
python manage.py test apps.blog.tests -v 2
```

Ожидаемый вывод: `Ran 5 tests in ...s OK`

- [ ] **Step 12: Commit**

```bash
git add apps/blog/ config/api.py
git commit -m "feat: blog app — BlogCategory, BlogPost with CKEditor5, API"
```

---

### Task 7: Promotions App

**Files:**
- Create: `apps/promotions/__init__.py`
- Create: `apps/promotions/apps.py`
- Create: `apps/promotions/models.py`
- Create: `apps/promotions/admin.py`
- Create: `apps/promotions/schemas.py`
- Create: `apps/promotions/api.py`
- Create: `apps/promotions/migrations/__init__.py`
- Create: `apps/promotions/tests.py`
- Modify: `config/api.py`

**Interfaces:**
- Consumes: `Branch` из `apps.branches.models`; `BranchFilterMixin` из `apps.users.mixins`
- Produces: `Promotion` model; `GET /api/v1/promotions/` (фильтр `?branch_id=`, только активные по дате)

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/promotions/migrations
touch apps/promotions/__init__.py apps/promotions/migrations/__init__.py
```

- [ ] **Step 2: Написать failing tests**

```python
# apps/promotions/tests.py
from django.test import TestCase, Client
from django.utils import timezone
from datetime import date, timedelta
from apps.branches.models import Branch
from apps.promotions.models import Promotion


class PromotionModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )

    def test_promotion_str(self):
        promo = Promotion.objects.create(
            title='Скидка 20%', starts_at=date.today(),
        )
        self.assertEqual(str(promo), 'Скидка 20%')


class PromotionAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )
        today = date.today()
        self.active = Promotion.objects.create(
            title='Активная акция', starts_at=today - timedelta(days=1),
            ends_at=today + timedelta(days=5), is_active=True,
        )
        self.active.branches.add(self.branch)

        self.expired = Promotion.objects.create(
            title='Устаревшая акция', starts_at=today - timedelta(days=10),
            ends_at=today - timedelta(days=1), is_active=True,
        )

    def test_list_promotions_returns_only_active(self):
        response = self.client.get('/api/v1/promotions/')
        self.assertEqual(response.status_code, 200)
        titles = [p['title'] for p in response.json()]
        self.assertIn('Активная акция', titles)
        self.assertNotIn('Устаревшая акция', titles)

    def test_filter_by_branch(self):
        response = self.client.get(f'/api/v1/promotions/?branch_id={self.branch.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Активная акция')
```

- [ ] **Step 3: Написать `apps/promotions/apps.py`**

```python
from django.apps import AppConfig


class PromotionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.promotions'
    verbose_name = 'Акции'
```

- [ ] **Step 4: Написать `apps/promotions/models.py`**

```python
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class Promotion(models.Model):
    title = models.CharField(max_length=500, verbose_name='Заголовок')
    description = CKEditor5Field('description', config_name='default', blank=True, verbose_name='Описание')
    banner = models.ImageField(upload_to='promotions/', blank=True, verbose_name='Баннер')
    starts_at = models.DateField(verbose_name='Начало')
    ends_at = models.DateField(null=True, blank=True, verbose_name='Окончание')
    branches = models.ManyToManyField(
        'branches.Branch', blank=True,
        related_name='promotions', verbose_name='Филиалы',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'
        ordering = ['-starts_at']

    def __str__(self):
        return self.title
```

- [ ] **Step 5: Написать `apps/promotions/schemas.py`**

```python
from ninja import Schema
from datetime import date
from typing import Optional


class PromotionSchema(Schema):
    id: int
    title: str
    banner: Optional[str] = None
    starts_at: date
    ends_at: Optional[date] = None
    is_active: bool

    @staticmethod
    def resolve_banner(obj):
        return obj.banner.url if obj.banner else None
```

- [ ] **Step 6: Написать `apps/promotions/api.py`**

```python
from ninja import Router
from typing import Optional
from django.utils import timezone
from django.db.models import Q
from .models import Promotion
from .schemas import PromotionSchema

router = Router(tags=['Promotions'])


@router.get('/', response=list[PromotionSchema])
def list_promotions(request, branch_id: Optional[int] = None):
    today = timezone.now().date()
    qs = Promotion.objects.filter(
        is_active=True,
        starts_at__lte=today,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=today))

    if branch_id:
        qs = qs.filter(branches__id=branch_id)

    return qs
```

- [ ] **Step 7: Написать `apps/promotions/admin.py`**

```python
from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'branches'
    list_display = ['title', 'starts_at', 'ends_at', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active', 'branches']
    search_fields = ['title']
    filter_horizontal = ['branches']

    def get_queryset(self, request):
        qs = admin.ModelAdmin.get_queryset(self, request)
        if request.user.is_superuser or request.user.role == 'superadmin':
            return qs
        branch = getattr(request.user, 'branch', None)
        if branch:
            return qs.filter(branches=branch).distinct()
        return qs.none()
```

- [ ] **Step 8: Добавить роутер в `config/api.py`**

Добавь в существующий `config/api.py`:

```python
from apps.promotions.api import router as promotions_router
api.add_router("/promotions/", promotions_router)
```

- [ ] **Step 9: Создать и применить миграции**

```bash
python manage.py makemigrations promotions
python manage.py migrate
```

- [ ] **Step 10: Запустить тесты**

```bash
python manage.py test apps.promotions.tests -v 2
```

Ожидаемый вывод: `Ran 3 tests in ...s OK`

- [ ] **Step 11: Commit**

```bash
git add apps/promotions/ config/api.py
git commit -m "feat: promotions app — Promotion with branch M2M, active-by-date API"
```

---

### Task 8: Appointments App

**Files:**
- Create: `apps/appointments/__init__.py`
- Create: `apps/appointments/apps.py`
- Create: `apps/appointments/models.py`
- Create: `apps/appointments/signals.py`
- Create: `apps/appointments/admin.py`
- Create: `apps/appointments/schemas.py`
- Create: `apps/appointments/api.py`
- Create: `apps/appointments/migrations/__init__.py`
- Create: `apps/appointments/tests.py`
- Modify: `config/api.py`

**Interfaces:**
- Consumes: `Branch` из `apps.branches.models`; `Doctor` из `apps.doctors.models`; `Service` из `apps.services.models`; `BranchFilterMixin`
- Produces: `Appointment` model с сигналом; `POST /api/v1/appointments/` (публичный)

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/appointments/migrations
touch apps/appointments/__init__.py apps/appointments/migrations/__init__.py
```

- [ ] **Step 2: Написать failing tests**

```python
# apps/appointments/tests.py
import json
from django.test import TestCase, Client
from apps.branches.models import Branch
from apps.appointments.models import Appointment


class AppointmentModelTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )

    def test_create_appointment(self):
        appt = Appointment.objects.create(
            patient_name='Иван Иванов',
            patient_phone='+7-999-111-2233',
            branch=self.branch,
        )
        self.assertEqual(appt.status, Appointment.Status.NEW)
        self.assertEqual(str(appt), 'Иван Иванов — Центральный')

    def test_default_status_is_new(self):
        appt = Appointment.objects.create(
            patient_name='Мария',
            patient_phone='+7-999-111-0000',
            branch=self.branch,
        )
        self.assertEqual(appt.status, Appointment.Status.NEW)


class AppointmentAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            name='Центральный', address='ул. Ленина, 1',
            phone='+7-999-000-0001', email='main@alexa.ru',
        )

    def test_create_appointment_via_api(self):
        payload = {
            'patient_name': 'Тест Тестов',
            'patient_phone': '+7-999-555-1234',
            'branch_id': self.branch.id,
            'comment': 'Болит зуб',
        }
        response = self.client.post(
            '/api/v1/appointments/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.count(), 1)
        appt = Appointment.objects.first()
        self.assertEqual(appt.patient_name, 'Тест Тестов')
        self.assertEqual(appt.status, Appointment.Status.NEW)

    def test_create_appointment_missing_required_field(self):
        payload = {'patient_name': 'Без телефона', 'branch_id': self.branch.id}
        response = self.client.post(
            '/api/v1/appointments/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 422)
```

- [ ] **Step 3: Написать `apps/appointments/apps.py`**

```python
from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.appointments'
    verbose_name = 'Записи на приём'

    def ready(self):
        import apps.appointments.signals  # noqa: F401
```

- [ ] **Step 4: Написать `apps/appointments/models.py`**

```python
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'in_progress', 'В обработке'
        DONE = 'done', 'Завершена'

    patient_name = models.CharField(max_length=255, verbose_name='Имя пациента')
    patient_phone = models.CharField(max_length=30, verbose_name='Телефон')
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.PROTECT,
        related_name='appointments', verbose_name='Филиал',
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='appointments', verbose_name='Врач',
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='appointments', verbose_name='Услуга',
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, verbose_name='Статус',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.patient_name} — {self.branch.name}'
```

- [ ] **Step 5: Написать `apps/appointments/signals.py`**

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment


def notify_telegram(appointment: Appointment) -> None:
    """Stub — implement when Telegram bot is connected."""
    pass


@receiver(post_save, sender=Appointment)
def on_appointment_created(sender, instance, created, **kwargs):
    if created:
        notify_telegram(instance)
```

- [ ] **Step 6: Написать `apps/appointments/schemas.py`**

```python
from ninja import Schema
from typing import Optional


class AppointmentCreateSchema(Schema):
    patient_name: str
    patient_phone: str
    branch_id: int
    doctor_id: Optional[int] = None
    service_id: Optional[int] = None
    comment: str = ''


class AppointmentResponseSchema(Schema):
    id: int
    patient_name: str
    status: str
```

- [ ] **Step 7: Написать `apps/appointments/api.py`**

```python
from ninja import Router
from django.shortcuts import get_object_or_404
from .models import Appointment
from .schemas import AppointmentCreateSchema, AppointmentResponseSchema
from apps.branches.models import Branch

router = Router(tags=['Appointments'])


@router.post('/', response={201: AppointmentResponseSchema})
def create_appointment(request, payload: AppointmentCreateSchema):
    branch = get_object_or_404(Branch, id=payload.branch_id, is_active=True)
    appt = Appointment.objects.create(
        patient_name=payload.patient_name,
        patient_phone=payload.patient_phone,
        branch=branch,
        doctor_id=payload.doctor_id,
        service_id=payload.service_id,
        comment=payload.comment,
    )
    return 201, appt
```

- [ ] **Step 8: Написать `apps/appointments/admin.py`**

```python
from django.contrib import admin
from apps.users.mixins import BranchFilterMixin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(BranchFilterMixin, admin.ModelAdmin):
    branch_filter_field = 'branch'
    list_display = ['patient_name', 'patient_phone', 'branch', 'doctor', 'service', 'status', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'branch']
    search_fields = ['patient_name', 'patient_phone']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
```

- [ ] **Step 9: Добавить роутер в `config/api.py`**

Добавь в существующий `config/api.py`:

```python
from apps.appointments.api import router as appointments_router
api.add_router("/appointments/", appointments_router)
```

- [ ] **Step 10: Создать и применить миграции**

```bash
python manage.py makemigrations appointments
python manage.py migrate
```

Ожидаемый вывод: `Applying appointments.0001_initial... OK`

- [ ] **Step 11: Запустить тесты**

```bash
python manage.py test apps.appointments.tests -v 2
```

Ожидаемый вывод: `Ran 4 tests in ...s OK`

- [ ] **Step 12: Commit**

```bash
git add apps/appointments/ config/api.py
git commit -m "feat: appointments app — Appointment model, Telegram stub signal, POST API"
```

---

### Task 9: Admin Panel Polish + Final Wiring

**Files:**
- Modify: `config/settings/base.py` — добавить `JAZZMIN_SETTINGS` и `JAZZMIN_UI_TWEAKS`
- Verify: `config/api.py` — все роутеры зарегистрированы
- Verify: `config/urls.py` — все маршруты настроены

**Interfaces:**
- Produces: полностью настроенная adminка с брендингом клиники; `/api/docs` показывает все эндпоинты; `/admin/` работает с jazzmin-темой

- [ ] **Step 1: Написать failing test для финального API**

```python
# Создай файл tests/test_api_smoke.py
# tests/__init__.py
```

```python
# tests/test_api_smoke.py
from django.test import TestCase, Client
from apps.branches.models import Branch
from apps.blog.models import BlogCategory, BlogPost
from django.utils import timezone


class APISmokeTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_docs_endpoint_accessible(self):
        response = self.client.get('/api/v1/docs')
        # Ninja redirects /docs to /docs/ or serves openapi.json
        self.assertIn(response.status_code, [200, 301, 302])

    def test_openapi_schema_accessible(self):
        response = self.client.get('/api/v1/openapi.json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        paths = data.get('paths', {})
        self.assertIn('/api/v1/branches/', paths)
        self.assertIn('/api/v1/doctors/', paths)
        self.assertIn('/api/v1/services/', paths)
        self.assertIn('/api/v1/blog/', paths)
        self.assertIn('/api/v1/promotions/', paths)
        self.assertIn('/api/v1/appointments/', paths)
```

- [ ] **Step 2: Запустить smoke тест, убедиться что падает**

```bash
python manage.py test tests.test_api_smoke -v 2
```

Ожидаемый вывод: `ImportError` или `ModuleNotFoundError: No module named 'tests'`

- [ ] **Step 3: Создать `tests/__init__.py`**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 4: Убедиться что все роутеры в `config/api.py`**

Финальное содержимое `config/api.py` должно быть:

```python
from ninja import NinjaAPI
from apps.branches.api import router as branches_router
from apps.doctors.api import router as doctors_router
from apps.services.api import router as services_router
from apps.blog.api import router as blog_router
from apps.promotions.api import router as promotions_router
from apps.appointments.api import router as appointments_router

api = NinjaAPI(
    title="Alexa Dental API",
    version="1.0.0",
    docs_url="/docs",
)

api.add_router("/branches/", branches_router)
api.add_router("/doctors/", doctors_router)
api.add_router("/services/", services_router)
api.add_router("/blog/", blog_router)
api.add_router("/promotions/", promotions_router)
api.add_router("/appointments/", appointments_router)
```

- [ ] **Step 5: Добавить `JAZZMIN_SETTINGS` в `config/settings/base.py`**

Добавь в конец `base.py`:

```python
JAZZMIN_SETTINGS = {
    "site_title": "Алекса Администрация",
    "site_brand": "Стоматология Алекса",
    "site_header": "Алекса",
    "welcome_sign": "Добро пожаловать в панель управления",
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "icons": {
        "auth": "fas fa-users-cog",
        "users.user": "fas fa-user",
        "branches.branch": "fas fa-clinic-medical",
        "doctors.doctor": "fas fa-user-md",
        "doctors.specialization": "fas fa-stethoscope",
        "services.servicecategory": "fas fa-list",
        "services.service": "fas fa-tooth",
        "blog.blogcategory": "fas fa-tag",
        "blog.blogpost": "fas fa-newspaper",
        "promotions.promotion": "fas fa-percent",
        "appointments.appointment": "fas fa-calendar-check",
    },
    "order_with_respect_to": [
        "branches",
        "users",
        "doctors",
        "services",
        "blog",
        "promotions",
        "appointments",
    ],
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
```

- [ ] **Step 6: Запустить все тесты**

```bash
python manage.py test apps.users.tests apps.branches.tests apps.doctors.tests apps.services.tests apps.blog.tests apps.promotions.tests apps.appointments.tests tests.test_api_smoke -v 2
```

Ожидаемый вывод: `Ran 21 tests in ...s OK`

- [ ] **Step 7: Запустить сервер и проверить вручную**

```bash
python manage.py createsuperuser
python manage.py runserver
```

Открой в браузере:
- `http://localhost:8000/admin/` — убедись что jazzmin-тема загружена, меню сгруппировано
- `http://localhost:8000/api/v1/docs` — убедись что все 7 секций эндпоинтов видны

- [ ] **Step 8: Финальный commit**

```bash
git add -A
git commit -m "feat: jazzmin admin config, CORS, smoke tests — backend complete"
```

---

## Итоговая проверка

После выполнения всех задач убедись:

```bash
# Все тесты зелёные
python manage.py test -v 2

# Нет незакрытых миграций
python manage.py migrate --check

# Django system check без ошибок
python manage.py check --deploy 2>/dev/null || python manage.py check
```

Проверь API вручную:
```bash
# Список филиалов
curl http://localhost:8000/api/v1/branches/

# Создание заявки
curl -X POST http://localhost:8000/api/v1/appointments/ \
  -H "Content-Type: application/json" \
  -d '{"patient_name": "Иван", "patient_phone": "+7-999-111-2233", "branch_id": 1}'
```
