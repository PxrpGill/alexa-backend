"""Отправка уведомлений о заявках в чат мессенджера MAX (Bot API)."""

import logging

import requests
from django.conf import settings
from django.urls import reverse

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
