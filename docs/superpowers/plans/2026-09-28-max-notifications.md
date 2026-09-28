# Уведомления о заявках в MAX — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** После создания любой заявки с публичного API отправлять уведомление с данными пациента и ссылкой на админку в общий чат мессенджера MAX.

**Architecture:** Общий клиент и форматтер живут в `apps/common/max.py`, отправка идёт Celery-задачей из `apps/common/tasks.py`. Каждое приложение с заявками подключает свой `post_save`-receiver в `signals.py`, который собирает текст и ставит уведомление в очередь через `transaction.on_commit`. Без токена и chat_id интеграция выключена и не делает ничего.

**Tech Stack:** Django 5.1.4, django-ninja, Celery + redis, `requests`, python-decouple.

**Spec:** `docs/superpowers/specs/2026-09-28-max-notifications-design.md`

## Global Constraints

- Язык проекта — русский: `verbose_name`, docstrings, сообщения и commit-сообщения на русском.
- Всё выполняется в контейнере: `docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test … -v 2 --keepdb`. Флаг `--keepdb` обязателен.
- Makefile использует standalone-бинарь `docker-compose`, не `docker compose`.
- `APPEND_SLASH = False`: путь в тесте — ровно путь запроса. `appointments`, `dms`, `consultation` — `/api/v1/<app>` без слэша; акции — `/api/v1/promotions/request`; отклики — `/api/v1/vacancies/apply` и `/api/v1/vacancies/{slug}/apply`.
- Под тестами Celery eager (`CELERY_TASK_ALWAYS_EAGER = "test" in sys.argv`), поэтому в тестах сигналов всегда мокается `apps.common.tasks.send_max_notification_task.delay` — иначе задача выполнится синхронно и уйдёт в сеть.
- Под тестами throttle не действует — обходить его в тестах не нужно.
- Новая зависимость строго одна: `requests==2.32.3`.
- Таймаут HTTP-запроса — 10 секунд, константа `REQUEST_TIMEOUT` в `apps/common/max.py`.
- Файл резюме в чат не отправляется никогда — только пометка «приложено/нет».
- Никаких миграций в этой ветке: модели не меняются.

## Review Focus

- **Заявка без филиала.** `Appointment.branch` — `null=True`. Строка «Филиал» должна просто отсутствовать, а не превращаться в «None» и не ронять отправку. Тест — в Задаче 4.
- **Отклик без вакансии.** `/vacancies/apply` создаёт `Application` с `vacancy=None` (`on_delete=SET_NULL`). Строка «Вакансия» отсутствует, уведомление уходит. Тест — в Задаче 7.
- **Отклик без резюме.** `resume` необязателен; в сообщении «Резюме: нет», ошибок нет. Тест — в Задаче 7.
- **MAX недоступен или отвечает 500.** Заявка всё равно сохранена, API вернул 201, исключение уходит в Celery на ретрай. Тест — в Задаче 2.
- **Брокер Celery недоступен.** `queue_max_notification` гасит исключение и логирует; `save()` и ответ API не затронуты. Тест — в Задаче 2.

---

### Задача 1: Настройки, зависимость и клиент MAX

**Files:**
- Create: `apps/common/max.py`
- Modify: `config/settings/base.py`, `requirements.txt`, `.env.example`, `docker/prod/.env.prod.example`
- Test: `apps/common/tests.py`

**Interfaces:**
- Consumes: —
- Produces: `send_max_message(text: str) -> None`; константа `REQUEST_TIMEOUT = 10`; настройки `MAX_API_URL`, `MAX_BOT_TOKEN`, `MAX_CHAT_ID`, `MAX_NOTIFICATIONS_ENABLED`, `SITE_URL`.

- [ ] **Шаг 1: Добавить зависимость**

В конец `requirements.txt`:

```
requests==2.32.3
```

Пересобрать образ, чтобы пакет появился в контейнере:

```bash
docker-compose -f docker/dev/docker-compose.yml build web
docker-compose -f docker/dev/docker-compose.yml up -d
```

- [ ] **Шаг 2: Написать падающий тест клиента**

В конец `apps/common/tests.py` (импорты `import requests` и `from apps.common.max import send_max_message` добавить к существующим сверху файла):

```python
@override_settings(
    MAX_API_URL="https://botapi.max.ru",
    MAX_BOT_TOKEN="token-123",
    MAX_CHAT_ID="-100500",
)
class SendMaxMessageTest(TestCase):
    @patch("apps.common.max.requests.post")
    def test_posts_text_to_max_bot_api(self, post):
        send_max_message("привет")

        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://botapi.max.ru/messages")
        self.assertEqual(
            kwargs["params"], {"access_token": "token-123", "chat_id": "-100500"}
        )
        self.assertEqual(kwargs["json"], {"text": "привет"})
        self.assertEqual(kwargs["timeout"], 10)

    @patch("apps.common.max.requests.post")
    def test_raises_on_error_response(self, post):
        post.return_value.raise_for_status.side_effect = requests.HTTPError("500")

        with self.assertRaises(requests.HTTPError):
            send_max_message("привет")

    @override_settings(MAX_API_URL="https://botapi.max.ru/")
    @patch("apps.common.max.requests.post")
    def test_strips_trailing_slash_in_api_url(self, post):
        send_max_message("привет")

        self.assertEqual(post.call_args[0][0], "https://botapi.max.ru/messages")
```

- [ ] **Шаг 3: Убедиться, что тест падает**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.common.tests.SendMaxMessageTest -v 2 --keepdb
```

Ожидание: FAIL — `ModuleNotFoundError: No module named 'apps.common.max'`.

- [ ] **Шаг 4: Добавить настройки**

В `config/settings/base.py` рядом с блоком Celery-настроек:

```python
# Уведомления о заявках в мессенджер MAX (apps/common/max.py).
MAX_API_URL = config("MAX_API_URL", default="https://botapi.max.ru")
MAX_BOT_TOKEN = config("MAX_BOT_TOKEN", default="")
MAX_CHAT_ID = config("MAX_CHAT_ID", default="")
MAX_NOTIFICATIONS_ENABLED = config(
    "MAX_NOTIFICATIONS_ENABLED",
    default=bool(MAX_BOT_TOKEN and MAX_CHAT_ID),
    cast=bool,
)

# Базовый адрес сайта — для ссылок на записи в админке в уведомлениях.
SITE_URL = config("SITE_URL", default="http://localhost:8000")
```

- [ ] **Шаг 5: Создать `apps/common/max.py`**

```python
"""Отправка уведомлений о заявках в чат мессенджера MAX (Bot API)."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger("apps.common.max")

REQUEST_TIMEOUT = 10


def send_max_message(text: str) -> None:
    """Отправить текстовое сообщение в чат MAX.

    Исключение при сетевой ошибке или не-2xx ответе пробрасывается наружу:
    его ловит Celery-задача и уходит в ретрай.
    """
    response = requests.post(
        f"{settings.MAX_API_URL.rstrip('/')}/messages",
        params={
            "access_token": settings.MAX_BOT_TOKEN,
            "chat_id": settings.MAX_CHAT_ID,
        },
        json={"text": text},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
```

- [ ] **Шаг 6: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.common.tests.SendMaxMessageTest -v 2 --keepdb
```

Ожидание: PASS (3 теста).

- [ ] **Шаг 7: Прописать переменные в env-шаблоны**

В `.env.example` и `docker/prod/.env.prod.example` добавить блок (в `docker/dev/.env.dev` — **не** добавлять, в деве интеграция выключена):

```
# Уведомления о заявках в мессенджер MAX.
# Пустой токен или чат = интеграция выключена.
MAX_BOT_TOKEN=
MAX_CHAT_ID=
MAX_API_URL=https://botapi.max.ru
# Базовый адрес сайта для ссылок на админку в уведомлениях.
SITE_URL=http://localhost:8000
```

В `docker/prod/.env.prod.example` значение `SITE_URL` — `https://example.com` с комментарием, что домен совпадает с `DOMAIN`.

- [ ] **Шаг 8: Проверка конфигурации и коммит**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web python manage.py check
git add requirements.txt config/settings/base.py apps/common/max.py apps/common/tests.py .env.example docker/prod/.env.prod.example
git commit -m "feat(notifications): клиент MAX Bot API и настройки интеграции"
```

---

### Задача 2: Celery-задача и постановка уведомления в очередь

**Files:**
- Modify: `apps/common/tasks.py`, `apps/common/max.py`
- Test: `apps/common/tests.py`

**Interfaces:**
- Consumes: `send_max_message(text: str) -> None` из Задачи 1.
- Produces: `send_max_notification_task(text: str)` (Celery-задача); `queue_max_notification(text: str) -> None`.

- [ ] **Шаг 1: Написать падающие тесты**

В `apps/common/tests.py` (импорт дополнить: `from apps.common.max import queue_max_notification, send_max_message`; `from apps.common.tasks import send_max_notification_task`):

```python
class QueueMaxNotificationTest(TestCase):
    @override_settings(MAX_NOTIFICATIONS_ENABLED=False)
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_does_nothing_when_integration_disabled(self, delay):
        queue_max_notification("привет")

        delay.assert_not_called()

    @override_settings(MAX_NOTIFICATIONS_ENABLED=True)
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_queues_task_when_enabled(self, delay):
        queue_max_notification("привет")

        delay.assert_called_once_with("привет")

    @override_settings(MAX_NOTIFICATIONS_ENABLED=True)
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_swallows_broker_errors(self, delay):
        delay.side_effect = OSError("broker is down")

        queue_max_notification("привет")  # исключение наружу не летит


class SendMaxNotificationTaskTest(TestCase):
    @override_settings(
        MAX_API_URL="https://botapi.max.ru",
        MAX_BOT_TOKEN="token-123",
        MAX_CHAT_ID="-100500",
    )
    @patch("apps.common.max.requests.post")
    def test_task_sends_message(self, post):
        send_max_notification_task("привет")

        post.assert_called_once()
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.common.tests.QueueMaxNotificationTest apps.common.tests.SendMaxNotificationTaskTest -v 2 --keepdb
```

Ожидание: FAIL — `ImportError: cannot import name 'queue_max_notification'`.

- [ ] **Шаг 3: Добавить задачу в `apps/common/tasks.py`**

```python
from apps.common.max import send_max_message


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def send_max_notification_task(text):
    """Отправить уведомление о заявке в чат MAX."""
    send_max_message(text)
```

- [ ] **Шаг 4: Добавить `queue_max_notification` в `apps/common/max.py`**

```python
def queue_max_notification(text: str) -> None:
    """Поставить уведомление в очередь.

    Импорт задачи — внутри функции, чтобы не ловить циклический импорт
    (`tasks` импортирует `send_max_message` из этого модуля).
    Недоступный брокер не должен ронять save() и ответ API.
    """
    if not settings.MAX_NOTIFICATIONS_ENABLED:
        return

    from apps.common.tasks import send_max_notification_task

    try:
        send_max_notification_task.delay(text)
    except Exception:
        logger.exception("Не удалось поставить уведомление MAX в очередь")
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.common -v 2 --keepdb
```

Ожидание: PASS, включая ранее написанные тесты клиента и существующие тесты картинок.

- [ ] **Шаг 6: Коммит**

```bash
git add apps/common/tasks.py apps/common/max.py apps/common/tests.py
git commit -m "feat(notifications): Celery-задача отправки уведомления в MAX"
```

---

### Задача 3: Форматирование сообщения и ссылка на админку

**Files:**
- Modify: `apps/common/max.py`
- Test: `apps/common/tests.py`

**Interfaces:**
- Consumes: настройка `SITE_URL` из Задачи 1.
- Produces: `admin_change_url(obj) -> str`; `format_lead_message(title: str, rows: list[tuple[str, str | None]], obj) -> str`.

- [ ] **Шаг 1: Написать падающие тесты**

В `apps/common/tests.py` (импорты дополнить: `from apps.common.max import admin_change_url, format_lead_message`; `from apps.appointments.models import Appointment`; `from apps.branch.models import BranchModel`):

```python
@override_settings(SITE_URL="https://alexa.ru")
class FormatLeadMessageTest(TestCase):
    def setUp(self):
        self.branch = BranchModel.objects.create(name="Центральный")
        self.appointment = Appointment.objects.create(
            patient_name="Иван Иванов",
            patient_phone="+79991234567",
            branch=self.branch,
            is_privacy_agreement=True,
        )

    def test_admin_change_url_points_to_object(self):
        url = admin_change_url(self.appointment)

        self.assertEqual(
            url,
            f"https://alexa.ru/admin/appointments/appointment/{self.appointment.pk}/change/",
        )

    @override_settings(SITE_URL="https://alexa.ru/")
    def test_admin_change_url_strips_trailing_slash(self):
        url = admin_change_url(self.appointment)

        self.assertNotIn("//admin", url.replace("https://", ""))

    def test_message_contains_title_rows_and_admin_link(self):
        text = format_lead_message(
            "🦷 Новая запись на приём",
            [("Имя", "Иван Иванов"), ("Телефон", "+79991234567")],
            self.appointment,
        )

        lines = text.split("\n")
        self.assertEqual(lines[0], "🦷 Новая запись на приём")
        self.assertIn("Имя: Иван Иванов", text)
        self.assertIn("Телефон: +79991234567", text)
        self.assertIn(
            f"Открыть в админке: https://alexa.ru/admin/appointments/appointment/{self.appointment.pk}/change/",
            text,
        )

    def test_message_skips_empty_rows(self):
        text = format_lead_message(
            "🦷 Новая запись на приём",
            [("Имя", "Иван Иванов"), ("Филиал", None), ("Страница", "")],
            self.appointment,
        )

        self.assertNotIn("Филиал", text)
        self.assertNotIn("Страница", text)
        self.assertNotIn("None", text)
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.common.tests.FormatLeadMessageTest -v 2 --keepdb
```

Ожидание: FAIL — `ImportError: cannot import name 'format_lead_message'`.

- [ ] **Шаг 3: Реализовать форматтер в `apps/common/max.py`**

Добавить `from django.urls import reverse` к импортам и функции:

```python
def admin_change_url(obj) -> str:
    """Абсолютная ссылка на страницу редактирования объекта в админке."""
    meta = obj._meta
    path = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[obj.pk])
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def format_lead_message(title: str, rows, obj) -> str:
    """Собрать текст уведомления о заявке.

    `rows` — пары («Подпись», значение). Пустые значения пропускаются,
    поэтому необязательные поля (филиал, вакансия) просто исчезают из текста.
    """
    lines = [title, ""]
    lines += [f"{label}: {value}" for label, value in rows if value]
    lines += ["", f"Открыть в админке: {admin_change_url(obj)}"]
    return "\n".join(lines)
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.common -v 2 --keepdb
```

Ожидание: PASS.

- [ ] **Шаг 5: Коммит**

```bash
git add apps/common/max.py apps/common/tests.py
git commit -m "feat(notifications): единый формат сообщения о заявке"
```

---

### Задача 4: Уведомления о записи на приём

**Files:**
- Modify: `apps/appointments/signals.py`
- Test: `apps/appointments/tests.py` (создать)

**Interfaces:**
- Consumes: `format_lead_message`, `queue_max_notification` из Задач 2–3.
- Produces: receiver `on_appointment_created`; образец сигнала, который копируют Задачи 5–7.

- [ ] **Шаг 1: Написать падающие тесты**

Создать `apps/appointments/tests.py`:

```python
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.branch.models import BranchModel


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class AppointmentMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(name="Центральный")

    def _payload(self, **overrides):
        payload = {
            "patient_name": "Иван Иванов",
            "patient_phone": "+79991234567",
            "branch_slug": self.branch.slug,
            "page_url": "/doctors",
            "is_ad_agreement": True,
            "is_privacy_agreement": True,
        }
        payload.update(overrides)
        return payload

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_appointment_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/appointments",
                self._payload(),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая запись на приём", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("+79991234567", text)
        self.assertIn("Центральный", text)
        self.assertIn("/admin/appointments/appointment/", text)

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_rejected_appointment_sends_nothing(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/appointments",
                self._payload(is_privacy_agreement=False),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        delay.assert_not_called()

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_appointment_without_branch_still_notifies(self, delay):
        from apps.appointments.models import Appointment

        with self.captureOnCommitCallbacks(execute=True):
            Appointment.objects.create(
                patient_name="Пётр Петров",
                patient_phone="+79990000000",
                branch=None,
                is_privacy_agreement=True,
            )

        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Пётр Петров", text)
        self.assertNotIn("Филиал", text)
        self.assertNotIn("None", text)
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.appointments -v 2 --keepdb
```

Ожидание: FAIL — `delay.assert_called_once()` падает, заглушка `notify_telegram` ничего не делает.

- [ ] **Шаг 3: Переписать `apps/appointments/signals.py`**

Заглушка `notify_telegram` удаляется целиком:

```python
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import format_lead_message, queue_max_notification

from .models import Appointment


@receiver(post_save, sender=Appointment)
def on_appointment_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новой записи на приём."""
    if not created:
        return

    text = format_lead_message(
        "🦷 Новая запись на приём",
        [
            ("Имя", instance.patient_name),
            ("Телефон", instance.patient_phone),
            ("Филиал", instance.branch.name if instance.branch else None),
            ("Страница", instance.page_url),
            (
                "Создана",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
    transaction.on_commit(lambda: queue_max_notification(text))
```

Текст собирается сразу, а в `on_commit` уходит уже готовая строка — так лямбда не держит объект и не ходит в БД после коммита.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.appointments -v 2 --keepdb
```

Ожидание: PASS (3 теста).

- [ ] **Шаг 5: Коммит**

```bash
git add apps/appointments/signals.py apps/appointments/tests.py
git commit -m "feat(appointments): уведомление в MAX о новой записи на приём"
```

---

### Задача 5: Уведомления о заявках ДМС и на консультацию

**Files:**
- Create: `apps/dms/signals.py`, `apps/consultation/signals.py`
- Modify: `apps/dms/apps.py`, `apps/consultation/apps.py`, `apps/dms/tests.py`, `apps/consultation/tests.py`

**Interfaces:**
- Consumes: `format_lead_message`, `queue_max_notification`.
- Produces: receivers `on_dms_created`, `on_consultation_created`.

- [ ] **Шаг 1: Написать падающие тесты для ДМС**

Заменить содержимое `apps/dms/tests.py`:

```python
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.branch.models import BranchModel


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class DMSMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(name="Центральный")

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_dms_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/dms",
                {
                    "patient_name": "Иван Иванов",
                    "patient_phone": "+79991234567",
                    "branch_slug": self.branch.slug,
                    "page_url": "/dms",
                    "is_ad_agreement": True,
                    "is_privacy_agreement": True,
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая заявка ДМС", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("Центральный", text)
        self.assertIn("/admin/dms/dms/", text)
```

- [ ] **Шаг 2: Написать падающие тесты для консультации**

Заменить содержимое `apps/consultation/tests.py`:

```python
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.branch.models import BranchModel


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class ConsultationMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = BranchModel.objects.create(name="Центральный")

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_consultation_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/consultation",
                {
                    "patient_name": "Иван Иванов",
                    "patient_phone": "+79991234567",
                    "branch_slug": self.branch.slug,
                    "page_url": "/",
                    "is_ad_agreement": True,
                    "is_privacy_agreement": True,
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая заявка на консультацию", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("/admin/consultation/consultation/", text)
```

- [ ] **Шаг 3: Убедиться, что тесты падают**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.dms apps.consultation -v 2 --keepdb
```

Ожидание: FAIL — `delay` не вызван, сигналов ещё нет.

- [ ] **Шаг 4: Создать `apps/dms/signals.py`**

```python
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import format_lead_message, queue_max_notification

from .models import DMS


@receiver(post_save, sender=DMS)
def on_dms_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новой заявке ДМС."""
    if not created:
        return

    text = format_lead_message(
        "🏥 Новая заявка ДМС",
        [
            ("Имя", instance.patient_name),
            ("Телефон", instance.patient_phone),
            ("Филиал", instance.branch.name if instance.branch else None),
            ("Страница", instance.page_url),
            (
                "Создана",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
    transaction.on_commit(lambda: queue_max_notification(text))
```

- [ ] **Шаг 5: Создать `apps/consultation/signals.py`**

```python
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import format_lead_message, queue_max_notification

from .models import Consultation


@receiver(post_save, sender=Consultation)
def on_consultation_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новой заявке на консультацию."""
    if not created:
        return

    text = format_lead_message(
        "💬 Новая заявка на консультацию",
        [
            ("Имя", instance.patient_name),
            ("Телефон", instance.patient_phone),
            ("Филиал", instance.branch.name if instance.branch else None),
            ("Страница", instance.page_url),
            (
                "Создана",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
    transaction.on_commit(lambda: queue_max_notification(text))
```

- [ ] **Шаг 6: Подключить сигналы в `apps.py`**

В `apps/dms/apps.py` добавить в класс `DmsConfig`:

```python
    def ready(self):
        import apps.dms.signals  # noqa: F401
```

В `apps/consultation/apps.py` добавить в класс `ConsultationConfig`:

```python
    def ready(self):
        import apps.consultation.signals  # noqa: F401
```

- [ ] **Шаг 7: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.dms apps.consultation -v 2 --keepdb
```

Ожидание: PASS (2 теста).

- [ ] **Шаг 8: Коммит**

```bash
git add apps/dms apps/consultation
git commit -m "feat(dms,consultation): уведомления в MAX о новых заявках"
```

---

### Задача 6: Уведомления о заявках на акцию

**Files:**
- Create: `apps/promotions/signals.py`, `apps/promotions/tests.py` (файла тестов в приложении сейчас нет)
- Modify: `apps/promotions/apps.py`

**Interfaces:**
- Consumes: `format_lead_message`, `queue_max_notification`.
- Produces: receiver `on_promotion_request_created`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `apps/promotions/tests.py`:

```python
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.promotions.models import Promotion


@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class PromotionRequestMaxNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.promotion = Promotion.objects.create(
            title="Чистка со скидкой",
            is_active=True,
            starts_at=timezone.localdate(),
        )

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_successful_request_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/promotions/request",
                {
                    "patient_name": "Иван Иванов",
                    "patient_phone": "+79991234567",
                    "slug": self.promotion.slug,
                    "is_ad_agreement": True,
                    "is_privacy_agreement": True,
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новая заявка на акцию", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("Чистка со скидкой", text)
        self.assertIn("/admin/promotions/promotionrequests/", text)
```

- [ ] **Шаг 2: Убедиться, что тест падает**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.promotions.tests.PromotionRequestMaxNotificationTest -v 2 --keepdb
```

Ожидание: FAIL — `delay` не вызван.

- [ ] **Шаг 3: Создать `apps/promotions/signals.py`**

У `PromotionRequests` нет поля `page_url` — строки «Страница» в сообщении нет.

```python
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import format_lead_message, queue_max_notification

from .models import PromotionRequests


@receiver(post_save, sender=PromotionRequests)
def on_promotion_request_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новой заявке на акцию."""
    if not created:
        return

    text = format_lead_message(
        "🎁 Новая заявка на акцию",
        [
            ("Имя", instance.patient_name),
            ("Телефон", instance.patient_phone),
            ("Акция", instance.promotion.title if instance.promotion else None),
            (
                "Создана",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
    transaction.on_commit(lambda: queue_max_notification(text))
```

- [ ] **Шаг 4: Подключить сигналы в `apps/promotions/apps.py`**

```python
    def ready(self):
        import apps.promotions.signals  # noqa: F401
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.promotions -v 2 --keepdb
```

Ожидание: PASS (1 тест).

- [ ] **Шаг 6: Коммит**

```bash
git add apps/promotions
git commit -m "feat(promotions): уведомление в MAX о заявке на акцию"
```

---

### Задача 7: Уведомления об откликах на вакансии

**Files:**
- Create: `apps/vacancies/signals.py`
- Modify: `apps/vacancies/apps.py`, `apps/vacancies/tests.py`

**Interfaces:**
- Consumes: `format_lead_message`, `queue_max_notification`.
- Produces: receiver `on_application_created`.

- [ ] **Шаг 1: Написать падающие тесты**

Дописать в конец `apps/vacancies/tests.py` (использует существующие `VacanciesBaseTestCase` и `make_resume`; добавить `from unittest.mock import patch` к импортам сверху файла):

```python
@override_settings(MAX_NOTIFICATIONS_ENABLED=True, SITE_URL="https://alexa.ru")
class ApplicationMaxNotificationTest(VacanciesBaseTestCase):
    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_apply_to_vacancy_queues_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/v1/vacancies/{self.vacancy.slug}/apply",
                {
                    "name": "Иван Иванов",
                    "phone": "+79991234567",
                    "privacy_policy_accepted": "true",
                    "resume": make_resume(),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Новый отклик на вакансию", text)
        self.assertIn("Иван Иванов", text)
        self.assertIn("+79991234567", text)
        self.assertIn("Ассистент стоматолога", text)
        self.assertIn("Резюме: приложено", text)
        self.assertIn("/admin/vacancies/application/", text)

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_general_apply_without_vacancy_and_resume(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/vacancies/apply",
                {
                    "name": "Пётр Петров",
                    "phone": "+79990000000",
                    "privacy_policy_accepted": "true",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        text = delay.call_args[0][0]
        self.assertIn("Пётр Петров", text)
        self.assertNotIn("Вакансия", text)
        self.assertIn("Резюме: нет", text)
        self.assertNotIn("None", text)

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_message_never_contains_resume_link_to_media(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/api/v1/vacancies/{self.vacancy.slug}/apply",
                {
                    "name": "Иван Иванов",
                    "phone": "+79991234567",
                    "privacy_policy_accepted": "true",
                    "resume": make_resume(),
                },
                format="multipart",
            )

        text = delay.call_args[0][0]
        self.assertNotIn("/media/", text)
        self.assertNotIn("vacancies/resumes/", text)

    @patch("apps.common.tasks.send_max_notification_task.delay")
    def test_rejected_apply_sends_nothing(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/vacancies/apply",
                {
                    "name": "Иван Иванов",
                    "phone": "+79991234567",
                    "privacy_policy_accepted": "false",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 400)
        delay.assert_not_called()
```

Если в файле уже настроен временный `MEDIA_ROOT` через `override_settings` на классах с загрузкой резюме — повторить тот же приём для этого класса, чтобы тестовые файлы не оседали в рабочем `media/`.

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.vacancies.tests.ApplicationMaxNotificationTest -v 2 --keepdb
```

Ожидание: FAIL — `delay` не вызван.

- [ ] **Шаг 3: Создать `apps/vacancies/signals.py`**

Файл резюме не отправляется — только пометка; скачивание идёт из админки через `download_resume` под `@staff_member_required`.

```python
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.common.max import format_lead_message, queue_max_notification

from .models import Application


@receiver(post_save, sender=Application)
def on_application_created(sender, instance, created, **kwargs):
    """Уведомить чат MAX о новом отклике на вакансию."""
    if not created:
        return

    text = format_lead_message(
        "📄 Новый отклик на вакансию",
        [
            ("Имя", instance.name),
            ("Телефон", instance.phone),
            ("Вакансия", instance.vacancy.name if instance.vacancy else None),
            ("Резюме", "приложено" if instance.resume else "нет"),
            (
                "Создан",
                timezone.localtime(instance.created_at).strftime("%d.%m.%Y %H:%M"),
            ),
        ],
        instance,
    )
    transaction.on_commit(lambda: queue_max_notification(text))
```

- [ ] **Шаг 4: Подключить сигналы в `apps/vacancies/apps.py`**

```python
    def ready(self):
        import apps.vacancies.signals  # noqa: F401
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python manage.py test apps.vacancies -v 2 --keepdb
```

Ожидание: PASS, включая существующие тесты вакансий и валидации резюме.

- [ ] **Шаг 6: Коммит**

```bash
git add apps/vacancies
git commit -m "feat(vacancies): уведомление в MAX о новом отклике"
```

---

### Задача 8: Документация и финальная проверка

**Files:**
- Modify: `CLAUDE.md`, `AGENTS.md`

**Interfaces:**
- Consumes: всё реализованное в Задачах 1–7.
- Produces: —

- [ ] **Шаг 1: Описать конвенцию в `CLAUDE.md`**

В раздел «Ключевые конвенции», сразу после подраздела «Lead-формы», добавить:

```markdown
### Уведомления о заявках в MAX
Каждая модель заявки шлёт уведомление в общий чат мессенджера MAX через
`post_save`-receiver в `signals.py` своего приложения (`apps.py:ready()` его импортирует).
Receiver собирает текст через `format_lead_message()` и ставит его в очередь
`transaction.on_commit(lambda: queue_max_notification(text))` — оба из `apps/common/max.py`.
Отправка идёт Celery-задачей `send_max_notification_task` с 3 ретраями; сбой брокера
или MAX не ломает `save()` и ответ API.

Выключено, пока не заданы `MAX_BOT_TOKEN` и `MAX_CHAT_ID` (`MAX_NOTIFICATIONS_ENABLED`),
поэтому дев и CI никуда не стучатся. Ссылка на запись в админке строится из `SITE_URL`.
Файл резюме в чат не отправляется — это защищённые ПД, только пометка «приложено».

Новый тип заявки → `signals.py` по образцу `apps/appointments/signals.py` + `ready()`
+ тест с `captureOnCommitCallbacks` и моком `send_max_notification_task.delay`.
```

Там же в разделе «Приложения» в строке `appointments` заменить «Telegram-signal stub» на «signal уведомления в MAX».

- [ ] **Шаг 2: Синхронизировать `AGENTS.md`**

Прочитать `AGENTS.md` и добавить в его раздел о конвенциях короткий абзац (2–3 строки) про то же: уведомления о заявках уходят в MAX через `post_save` + Celery, код — в `apps/common/max.py`, выключено без токена.

- [ ] **Шаг 3: Прогнать весь набор тестов и проверку**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web python manage.py check
docker-compose -f docker/dev/docker-compose.yml exec web python manage.py test -v 2 --keepdb
```

Ожидание: `check` без ошибок, все тесты зелёные. Отдельно убедиться, что `tests/test_api_smoke.py` проходит — роуты не менялись, он должен остаться зелёным без правок.

- [ ] **Шаг 4: Убедиться, что в дев-окружении интеграция выключена**

```bash
docker-compose -f docker/dev/docker-compose.yml exec web \
  python -c "from django.conf import settings; import django; django.setup(); print(settings.MAX_NOTIFICATIONS_ENABLED)"
```

Ожидание: `False` (в `docker/dev/.env.dev` токена нет).

- [ ] **Шаг 5: Коммит**

```bash
git add CLAUDE.md AGENTS.md
git commit -m "docs: конвенция уведомлений о заявках в MAX"
```

---

## Ручная проверка перед мержем

Автотесты не ходят в сеть, поэтому боевую отправку надо проверить руками один раз:

1. В `docker/dev/.env.dev` временно прописать настоящие `MAX_BOT_TOKEN` и `MAX_CHAT_ID`, перезапустить `web` и `worker` (`make dev-down && make dev-up`).
2. Отправить заявку: `curl -X POST http://localhost:8000/api/v1/appointments -H 'Content-Type: application/json' -d '{"patient_name":"Тест","patient_phone":"+79990000000","branch_slug":"<slug филиала>","page_url":"/","is_ad_agreement":true,"is_privacy_agreement":true}'`
3. Убедиться, что сообщение пришло в чат MAX и ссылка на админку открывается.
4. **Убрать токен из `docker/dev/.env.dev`** — он не должен попасть в коммит. Проверить `git status` и `git diff` перед пушем.
