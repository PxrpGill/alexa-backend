"""Общая логика lead-форм (appointments, dms, consultation)."""

from django.conf import settings


def build_page_url(request, page_url) -> str:
    """Абсолютная ссылка на страницу сайта, с которой пришла заявка.

    Фронтенд живёт на отдельном домене, поэтому `request.build_absolute_uri()`
    приклеил бы к пути домен бэкенда, и ссылка вела бы в никуда.
    `FRONTEND_URL` задаёт домен сайта; пока она не задана, поведение прежнее.
    Абсолютную ссылку от клиента оставляем как есть — в ней могут быть
    query-параметры рекламных меток.
    """
    if not page_url:
        return "/"

    if page_url.startswith(("http://", "https://")):
        return page_url

    if settings.FRONTEND_URL:
        return f"{settings.FRONTEND_URL.rstrip('/')}/{page_url.lstrip('/')}"

    return request.build_absolute_uri(page_url)
