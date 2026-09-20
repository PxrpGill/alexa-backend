import functools
import sys
import time

from django.core.cache import cache


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

            ip = request.META.get("REMOTE_ADDR", "unknown")
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
