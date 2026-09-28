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
