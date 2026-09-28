"""Отправка уведомлений о заявках в чат мессенджера MAX (Bot API)."""

import logging

import requests
from django.conf import settings
from django.db import transaction
from django.urls import reverse

logger = logging.getLogger("apps.common.max")

REQUEST_TIMEOUT = 10


class MaxDeliveryError(Exception):
    """Не удалось доставить сообщение в MAX.

    Собственный класс нужен, чтобы наружу не уходил текст исключения
    `requests`: он может содержать URL и детали запроса, а оттуда всё
    попадает в логи Celery.
    """


def send_max_message(text: str) -> None:
    """Отправить текстовое сообщение в чат MAX.

    При сетевой ошибке или не-2xx ответе поднимает MaxDeliveryError —
    его ловит Celery-задача и уходит в ретрай.
    """
    if not settings.MAX_BOT_TOKEN or not settings.MAX_CHAT_ID:
        logger.error("MAX_BOT_TOKEN или MAX_CHAT_ID не заданы — уведомление не отправлено")
        return

    url = f"{settings.MAX_API_URL.rstrip('/')}/messages"
    try:
        response = requests.post(
            url,
            # Токен — сырой строкой в заголовке, без префикса «Bearer»
            # (с ним API отвечает 401). Передача через query-параметр
            # access_token больше не поддерживается.
            headers={"Authorization": settings.MAX_BOT_TOKEN},
            params={"chat_id": settings.MAX_CHAT_ID},
            json={"text": text},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise MaxDeliveryError(
            f"Запрос к MAX API не удался: {type(exc).__name__}"
        ) from None

    if not response.ok:
        raise MaxDeliveryError(f"MAX API вернул {response.status_code}")


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


def queue_lead_notification(title: str, rows, obj) -> None:
    """Собрать уведомление о заявке и поставить его в очередь после коммита.

    Вызывается из post_save-сигналов. Сбой сборки текста (например, модель
    сняли с регистрации в админке и reverse перестал работать) не должен
    превращаться в ошибку ответа: заявка уже сохранена, и повторная отправка
    формы пациентом породила бы дубль.
    """
    try:
        text = format_lead_message(title, rows, obj)
    except Exception:
        logger.exception("Не удалось собрать уведомление MAX о заявке %s", obj.pk)
        return

    transaction.on_commit(lambda: queue_max_notification(text))
