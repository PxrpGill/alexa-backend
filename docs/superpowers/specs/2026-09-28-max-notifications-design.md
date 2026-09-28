# Уведомления о заявках в мессенджер MAX

Дата: 2026-09-28
Статус: согласовано, к реализации

## Задача

После каждой успешно созданной заявки с публичного API отправлять уведомление
в чат мессенджера MAX, где сидит ответственный круг сотрудников клиники.
Сейчас единственный след этой идеи — заглушка `notify_telegram()` в
`apps/appointments/signals.py`; она заменяется реальной отправкой.

Цель — администратор видит заявку в чате и звонит пациенту, не заходя в админку.

## Что уже есть (входные условия)

- Бот в MAX создан, токен и `chat_id` чата на руках, бот добавлен в чат.
  Интеграция — через MAX Bot API (`https://platform-api2.max.ru`).
- Пять типов заявок с одинаковым контрактом lead-форм:
  `Appointment`, `DMS`, `Consultation`, `PromotionRequests`, `Application` (отклик на вакансию).
- Celery с redis-брокером, под тестами — eager.
- HTTP-клиента в зависимостях нет.

## Решения

| Вопрос | Решение |
|---|---|
| Точка перехвата | `post_save`-сигнал на каждой модели заявки (развитие существующего паттерна в `appointments`) |
| Маршрутизация | Один общий чат из настроек; разбивки по филиалам нет |
| Состав сообщения | Полные данные, включая телефон, плюс ссылка на запись в админке |
| Доставка | Celery-задача с ретраями, а не синхронный запрос в обработчике API |
| Резюме откликов | Файл не прикладывается — это защищённые ПД; в чат идёт только пометка «приложено» и ссылка в админку |

Осознанное следствие выбора `post_save`: уведомление уйдёт и о заявке,
заведённой вручную в админке. Это признано приемлемым.

## Архитектура

### Общая инфраструктура — `apps/common`

**`apps/common/max.py`**

- `send_max_message(text: str) -> None`
  `POST {MAX_API_URL}/messages` с токеном в заголовке `Authorization` (сырой строкой,
  без префикса `Bearer` — с ним API отвечает 401), `chat_id` query-параметром
  и телом `{"text": text}`. Таймаут 10 секунд.
  Не-2xx и сетевая ошибка поднимают `MaxDeliveryError` — текст исключения `requests`
  наружу не уходит, чтобы детали запроса не оседали в логах. Ошибку ловит Celery и ретраит.
  При пустом `MAX_BOT_TOKEN` или `MAX_CHAT_ID` запрос не отправляется вовсе.
- `queue_max_notification(text: str) -> None`
  Если `settings.MAX_NOTIFICATIONS_ENABLED` ложно — молча выходит.
  Иначе ставит `send_max_notification_task.delay(text)` внутри `try/except Exception`
  с `logger.exception` — недоступный брокер не должен ронять `save()` и ответ API
  (тот же приём, что в `ImageVariantsMixin`).
- `format_lead_message(title: str, rows: list[tuple[str, str]], obj) -> str`
  Собирает единый текст: заголовок, пары «Поле: значение», ссылку на объект в админке
  через `reverse('admin:<app>_<model>_change', args=[obj.pk])` и `settings.SITE_URL`.
  Строки со значением `None`/пустой строкой пропускаются.

Логгер — `logging.getLogger("apps.common.max")`.

**`apps/common/tasks.py`** — рядом с существующей задачей:

```python
@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def send_max_notification_task(text: str) -> None:
    send_max_message(text)
```

### Подключение в приложениях

В каждом из `appointments`, `dms`, `consultation`, `promotions`, `vacancies`:

- `signals.py` — receiver `post_save`:

```python
@receiver(post_save, sender=Appointment)
def on_appointment_created(sender, instance, created, **kwargs):
    if not created:
        return
    text = format_lead_message("🦷 Новая запись на приём", [...], instance)
    transaction.on_commit(lambda: queue_max_notification(text))
```

  `transaction.on_commit` — чтобы не уведомлять о заявке, чья транзакция откатилась.
  Текст собирается синхронно, до `on_commit`, пока объект гарантированно доступен.

- `apps.py` → `ready()` импортирует `signals` (в `appointments` уже есть;
  остальным четырём добавляется).

В `appointments/signals.py` заглушка `notify_telegram()` удаляется.

### Формат сообщения

```
🦷 Новая запись на приём

Имя: Иван Иванов
Телефон: +7 999 123-45-67
Филиал: Центральный
Страница: https://alexa.ru/doctors
Создана: 28.09.2026 14:32

Открыть в админке: https://alexa.ru/admin/appointments/appointment/12/change/
```

Plain text, без markdown/html — не нужно экранирование пользовательского ввода.
Время — `timezone.localtime`, формат `d.m.Y H:i`.

Заголовки и специфичные строки по типам:

| Модель | Заголовок | Специфичная строка |
|---|---|---|
| `Appointment` | 🦷 Новая запись на приём | Филиал |
| `DMS` | 🏥 Новая заявка ДМС | Филиал |
| `Consultation` | 💬 Новая заявка на консультацию | Филиал |
| `PromotionRequests` | 🎁 Новая заявка на акцию | Акция |
| `Application` | 📄 Новый отклик на вакансию | Вакансия, «Резюме: приложено / нет» |

У `Appointment` филиал может быть `null`, у `Application` вакансия — `null`
(`on_delete=SET_NULL`): такие строки просто не попадают в сообщение.
У `PromotionRequests` и `Application` нет `page_url` — строка отсутствует.

### Настройки

`config/settings/base.py`:

```python
MAX_API_URL = config("MAX_API_URL", default="https://platform-api2.max.ru")
MAX_BOT_TOKEN = config("MAX_BOT_TOKEN", default="")
MAX_CHAT_ID = config("MAX_CHAT_ID", default="")
MAX_NOTIFICATIONS_ENABLED = config(
    "MAX_NOTIFICATIONS_ENABLED",
    default=bool(MAX_BOT_TOKEN and MAX_CHAT_ID),
    cast=bool,
)
SITE_URL = config("SITE_URL", default="http://localhost:8000")
```

Без токена и чата интеграция выключена по умолчанию: дев-окружение, CI и тесты
никуда не стучатся и не падают. Переменные добавляются в `.env.example`
(с пустыми значениями и комментарием) и `docker/prod/.env.prod.example`;
в `docker/dev/.env.dev` не добавляются — в деве фича выключена.

Новая зависимость в `requirements.txt`: `requests==2.32.3`.

## Обработка ошибок

| Сбой | Поведение |
|---|---|
| Интеграция не настроена | `queue_max_notification` выходит сразу, без логов |
| Брокер недоступен | `logger.exception`, `save()` и ответ API не затронуты |
| MAX ответил не-2xx / таймаут | Исключение → Celery ретраит 3 раза с backoff → задача умирает, `logger.error` |
| Транзакция откатилась | Уведомление не отправляется (`on_commit`) |

Заявка всегда сохраняется в БД независимо от судьбы уведомления — чат
это удобство, а не источник истины.

## Тестирование

`apps/common/tests.py`:
- `send_max_message` с замоканным `requests.post`: проверяются URL, `access_token`
  и `chat_id` в params, тело `{"text": ...}`, таймаут; на 500 — исключение.
- `queue_max_notification`: при `MAX_NOTIFICATIONS_ENABLED=False` задача не ставится;
  при исключении из `.delay()` наружу ничего не летит.
- `format_lead_message`: заголовок, пропуск пустых строк, корректная ссылка в админку.

По приложениям (`appointments`, `dms`, `consultation`, `promotions`, `vacancies`):
- POST на публичный endpoint внутри `captureOnCommitCallbacks(execute=True)`
  при `override_settings(MAX_NOTIFICATIONS_ENABLED=True)` и замоканном
  `send_max_notification_task` — проверяется факт вызова и ключевые подстроки текста
  (имя, телефон, филиал/акция/вакансия).
- Пустые заготовки `apps/dms/tests.py` и `apps/consultation/tests.py` заполняются.

Реальных HTTP-запросов в тестах нет. Разработка по TDD: тест → реализация.

## История контракта API

Первая редакция этой спеки фиксировала домен `botapi.max.ru` и токен в query-параметре
`access_token`. Сверка с документацией MAX перед боевым запуском показала, что схема
устарела: домен переехал `botapi.max.ru` → `platform-api.max.ru` → `platform-api2.max.ru`
(последний переезд 19 июля 2026), а передача токена через query-параметры больше
не поддерживается — только заголовок `Authorization`. Контракт выше отражает актуальную
схему. Моки в тестах подтверждают наши допущения, а не реальное API, поэтому боевая
отправка проверяется вручную (см. план).

## Что не входит

- Разбивка по филиалам или типам заявок на разные чаты.
- Приём сообщений от бота (webhook, команды, кнопки).
- Отправка файла резюме в чат.
- Уведомления о смене статуса заявки — только о создании.
- Замена или дублирование уведомлений в другие каналы (email, Telegram).

## Затрагиваемые файлы

Новые: `apps/common/max.py`, `signals.py` в `dms`, `consultation`, `promotions`, `vacancies`,
спека в `docs/superpowers/specs/`.

Изменяемые: `apps/common/tasks.py`, `apps/common/tests.py`, `apps/appointments/signals.py`,
`apps.py` четырёх приложений, `config/settings/base.py`, `requirements.txt`,
`.env.example`, `docker/prod/.env.prod.example`, `tests.py` пяти приложений,
`CLAUDE.md` и `AGENTS.md` (раздел про lead-формы и новую конвенцию уведомлений).
