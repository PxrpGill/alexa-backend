import sys
from pathlib import Path

from decouple import config
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

DJANGO_APPS = [
    # Тема админки. Обязательно раньше django.contrib.admin: подменяет AdminSite.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "ninja",
    "corsheaders",
    "django_ckeditor_5",
    "nested_admin",
]

LOCAL_APPS = [
    "apps.common",
    "apps.users",
    "apps.doctors",
    "apps.blog",
    "apps.promotions",
    "apps.appointments",
    "apps.dms",
    "apps.consultation",
    "apps.branch",
    "apps.vacancies",
    "apps.stories",
    "apps.pages",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="alexa"),
        "USER": config("DB_USER", default="alexa"),
        "PASSWORD": config("DB_PASSWORD", default="alexa"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        # Соединение живёт между запросами: ISR фронтенда раз в минуту бьёт
        # пачкой GET-запросов, и открывать подключение на каждый — лишняя задержка.
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MAX_RESUME_SIZE = config("MAX_RESUME_SIZE", default=5 * 1024 * 1024, cast=int)
# Лимиты загрузки видео сторисов. Размер тела запроса к /admin/ в nginx
# (client_max_body_size) должен быть не меньше MAX_STORY_VIDEO_SIZE.
MAX_STORY_VIDEO_SIZE = config("MAX_STORY_VIDEO_SIZE", default=100 * 1024 * 1024, cast=int)
MAX_STORY_VIDEO_SECONDS = 60

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config(
            "REDIS_URL",
            default=config("CELERY_BROKER_URL", default="redis://localhost:6379/0"),
        ),
    }
}

# Отдавать защищённые файлы (резюме) через nginx X-Accel-Redirect вместо
# стриминга из Django. Требует internal-location в nginx.conf.
USE_X_ACCEL_REDIRECT = config("USE_X_ACCEL_REDIRECT", default=not DEBUG, cast=bool)

# Доверять X-Real-IP / X-Forwarded-For при определении IP клиента
# (apps/common/throttling.py). Включать только когда перед Django стоит nginx:
# иначе клиент сможет подделать заголовок и обойти rate limit.
TRUST_PROXY_HEADERS = config("TRUST_PROXY_HEADERS", default=not DEBUG, cast=bool)

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ALWAYS_EAGER = "test" in sys.argv

# Постановка задачи выполняется синхронно в HTTP-запросе (ATOMIC_REQUESTS выключен,
# поэтому transaction.on_commit срабатывает сразу), а уведомления о заявках ставятся
# прямо на пути публичной формы. Зависший брокер не должен держать ответ:
# без ретраев публикации и с короткими таймаутами сокета.
CELERY_TASK_PUBLISH_RETRY = False
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": 2,
    "socket_timeout": 2,
}

# Уведомления о заявках в мессенджер MAX (apps/common/max.py).
MAX_API_URL = config("MAX_API_URL", default="https://platform-api.max.ru")
MAX_BOT_TOKEN = config("MAX_BOT_TOKEN", default="")
MAX_CHAT_ID = config("MAX_CHAT_ID", default="")
MAX_NOTIFICATIONS_ENABLED = config(
    "MAX_NOTIFICATIONS_ENABLED",
    default=bool(MAX_BOT_TOKEN and MAX_CHAT_ID),
    cast=bool,
)

# Базовый адрес сайта — для ссылок на записи в админке в уведомлениях.
SITE_URL = config("SITE_URL", default="http://localhost:8000")

# Домен публичного сайта (Next.js живёт отдельно от бэкенда). Используется
# в apps/common/leads.py, чтобы «Откуда сделана заявка» вело на сайт, а не на API.
# Пусто — ссылка строится от домена входящего запроса, как раньше.
FRONTEND_URL = config("FRONTEND_URL", default="")

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": {
            "items": [
                "heading",
                "|",
                "bold",
                "italic",
                "underline",
                "|",
                "link",
                "|",
                "bulletedList",
                "numberedList",
                "|",
                "blockQuote",
                "|",
                "imageUpload",
                "|",
                "insertTable",
                "|undo",
                "redo",
            ],
        },
    },
    "blog_content": {
        "toolbar": {
            "items": [
                "bold",
                "italic",
                "underline",
                "|",
                "bulletedList",
                "numberedList",
                "|",
                "heading",
            ],
        },
        "heading": {
            "options": [
                {
                    "model": "paragraph",
                    "title": "Paragraph",
                    "class": "ck-heading_paragraph",
                },
                {
                    "model": "heading2",
                    "view": "h2",
                    "title": "Heading 2",
                    "class": "ck-heading_heading2",
                },
            ],
        },
    },
}

# Тулбар любого CKEditor «прилипает» к верху окна. CKEditor делает это сам
# (position: fixed у .ck-sticky-panel__content_sticky), поэтому прилипание
# работает и внутри Unfold-обёртки .form-rows с overflow: hidden, где CSS
# position: sticky бесполезен. top: 0 — у Unfold нет залипающей шапки
# (в jazzmin было 70px). Цикл задаёт значение по умолчанию и новым конфигам.
for _editor_config in CKEDITOR_5_CONFIGS.values():
    _editor_config.setdefault("ui", {}).setdefault("viewportOffset", {}).setdefault(
        "top", 0
    )

CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

UNFOLD = {
    "SITE_TITLE": "Алекса Администрация",
    "SITE_HEADER": "Стоматология Алекса",
    "SITE_SUBHEADER": "Панель управления",
    "SITE_URL": "/admin/",
    "SITE_SYMBOL": "medical_services",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    # CKEditor: прилипающая панель инструментов (см. static/css/ckeditor5.css).
    "STYLES": [lambda request: static("css/ckeditor5.css")],
    "SIDEBAR": {
        "show_search": True,
        "command_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Пользователи",
                "separator": True,
                "items": [
                    {
                        "title": "Пользователи",
                        "icon": "person",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": "Группы",
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": "Клиника",
                "separator": True,
                "items": [
                    {
                        "title": "Сотрудники",
                        "icon": "medical_services",
                        "link": reverse_lazy("admin:doctors_doctor_changelist"),
                    },
                    {
                        "title": "Филиалы",
                        "icon": "store",
                        "link": reverse_lazy("admin:branch_branchmodel_changelist"),
                    },
                    {
                        "title": "Страницы сайта",
                        "icon": "web",
                        "link": reverse_lazy("admin:branch_pagesmodel_changelist"),
                    },
                ],
            },
            {
                "title": "Контент",
                "separator": True,
                "items": [
                    {
                        "title": "Статьи",
                        "icon": "article",
                        "link": reverse_lazy("admin:blog_blogpost_changelist"),
                    },
                    {
                        "title": "Категории блога",
                        "icon": "category",
                        "link": reverse_lazy("admin:blog_blogcategory_changelist"),
                    },
                    {
                        "title": "Акции",
                        "icon": "sell",
                        "link": reverse_lazy("admin:promotions_promotion_changelist"),
                    },
                    {
                        "title": "Сторисы",
                        "icon": "play_circle",
                        "link": reverse_lazy("admin:stories_storygroup_changelist"),
                    },
                ],
            },
            {
                "title": "Заявки",
                "separator": True,
                "items": [
                    {
                        "title": "Записи на приём",
                        "icon": "event_available",
                        "link": reverse_lazy("admin:appointments_appointment_changelist"),
                    },
                    {
                        "title": "Заявки на акции",
                        "icon": "redeem",
                        "link": reverse_lazy(
                            "admin:promotions_promotionrequests_changelist"
                        ),
                    },
                    {
                        "title": "Заявки ДМС",
                        "icon": "assignment",
                        "link": reverse_lazy("admin:dms_dms_changelist"),
                    },
                    {
                        "title": "Заявки на консультацию",
                        "icon": "support_agent",
                        "link": reverse_lazy(
                            "admin:consultation_consultation_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "Вакансии",
                "separator": True,
                "items": [
                    {
                        "title": "Вакансии",
                        "icon": "work",
                        "link": reverse_lazy("admin:vacancies_vacancy_changelist"),
                    },
                    {
                        "title": "Категории вакансий",
                        "icon": "cases",
                        "link": reverse_lazy(
                            "admin:vacancies_vacancycategory_changelist"
                        ),
                    },
                    {
                        "title": "Отклики",
                        "icon": "description",
                        "link": reverse_lazy("admin:vacancies_application_changelist"),
                    },
                ],
            },
            {
                "title": "Страницы: Ландышевая",
                "separator": True,
                "items": [
                    {
                        "title": "Главная страница",
                        "icon": "home",
                        "link": reverse_lazy(
                            "admin:pages_landyshevayamainpagemodel_changelist"
                        ),
                    },
                    {
                        "title": "Взрослым",
                        "icon": "person",
                        "items": [
                            {
                                "title": "Консультация",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadultconsultationmodel_changelist"
                                ),
                            },
                            {
                                "title": "Гнатология",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadultgnathologymodel_changelist"
                                ),
                            },
                            {
                                "title": "Гигиена",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadulthygienemodel_changelist"
                                ),
                            },
                            {
                                "title": "Ортодонтия",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadultorthodonticsmodel_changelist"
                                ),
                            },
                            {
                                "title": "Ортопедия",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadultorthopedicsmodel_changelist"
                                ),
                            },
                            {
                                "title": "Пародонтология",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadultperiodontologymodel_changelist"
                                ),
                            },
                            {
                                "title": "Хирургия и имплантация",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadultsurgeryandimplantationmodel_changelist"
                                ),
                            },
                            {
                                "title": "Терапия",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadulttherapymodel_changelist"
                                ),
                            },
                            {
                                "title": "Лечение во сне",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayaadulttreatmentduringsleepmodel_changelist"
                                ),
                            },
                        ],
                    },
                    {
                        "title": "Детям",
                        "icon": "child_care",
                        "items": [
                            {
                                "title": "Консультация",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayapediatricconsultationmodel_changelist"
                                ),
                            },
                            {
                                "title": "Гигиена",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayapediatrichygienemodel_changelist"
                                ),
                            },
                            {
                                "title": "Ортодонтия",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayapediatricorthodonticsmodel_changelist"
                                ),
                            },
                            {
                                "title": "Хирургия и имплантация",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayapediatricsurgeryandimplantationmodel_changelist"
                                ),
                            },
                            {
                                "title": "Терапия",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayapediatrictherapymodel_changelist"
                                ),
                            },
                            {
                                "title": "Лечение во сне",
                                "link": reverse_lazy(
                                    "admin:pages_landyshevayapediatrictreatmentduringsleepmodel_changelist"
                                ),
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Страницы: Волкова",
                "separator": True,
                "items": [
                    {
                        "title": "Главная страница",
                        "icon": "home",
                        "link": reverse_lazy(
                            "admin:pages_volkovamainpagemodel_changelist"
                        ),
                    },
                ],
            },
        ],
    },
}
