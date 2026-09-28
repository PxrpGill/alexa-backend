import functools
import sys
import time

from django.conf import settings
from django.core.cache import cache


def get_client_ip(request):
    """Реальный IP клиента с учётом обратного прокси.

    За nginx ``REMOTE_ADDR`` — это адрес контейнера nginx, один и тот же для всех
    посетителей, поэтому лимит по нему становится общим на всех сразу.

    ``TRUST_PROXY_HEADERS`` включается только там, где перед Django реально стоит
    прокси: nginx перезаписывает ``X-Real-IP`` своим ``$remote_addr``, подделать
    его извне нельзя. В ``X-Forwarded-For`` доверяем лишь последнему элементу —
    его добавляет наш nginx, начало цепочки клиент может подставить сам.
    """
    if getattr(settings, 'TRUST_PROXY_HEADERS', False):
        real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
        if real_ip:
            return real_ip

        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            return forwarded_for.split(',')[-1].strip()

    return request.META.get('REMOTE_ADDR', 'unknown')


def throttle(
    limit: int,
    window_seconds: int,
    *,
    message: str = "Слишком много запросов. Попробуйте позже.",
):
    """Ограничивает число запросов с одного IP за окно времени (Django cache).

    Используется для публичных POST-endpoints. Ключ — IP + имя функции.
    В тестах (``test`` в sys.argv) ограничение не применяется, как и Celery
    eager-режим в config/settings/base.py.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if "test" in sys.argv:
                return view_func(request, *args, **kwargs)

            ip = get_client_ip(request)
            key = f"throttle:{view_func.__name__}:{ip}"
            now = time.time()

            try:
                hits = cache.get(key, [])
            except Exception:
                hits = []

            hits = [ts for ts in hits if ts > now - window_seconds]
            if len(hits) >= limit:
                return 429, {"message": message}

            hits.append(now)
            try:
                cache.set(key, hits, window_seconds)
            except Exception:
                pass

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


LEAD_FORM_LIMIT = 10
LEAD_FORM_WINDOW = 60
LEAD_FORM_MESSAGE = "Слишком много заявок. Попробуйте позже."


def throttle_lead_form(view_func):
    """Общий лимит для публичных форм-заявок: 10 отправок с одного IP в минуту.

    Навешивать на каждый новый POST-endpoint формы; в ``response`` роута при этом
    обязательно объявить ``429: ErrorResponseMessageSchema``.
    """
    return throttle(LEAD_FORM_LIMIT, LEAD_FORM_WINDOW, message=LEAD_FORM_MESSAGE)(
        view_func
    )
