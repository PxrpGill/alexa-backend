from ninja.renderers import JSONRenderer

from apps.common.typography import typograph_data


class TypographJSONRenderer(JSONRenderer):
    """JSON-renderer, который типографирует все тексты в ответах API.

    Единственная точка применения русской типографики: в БД и админке лежит
    исходный текст редактора, а фронтенд всегда получает обработанный.
    Служебные поля (slug, ссылки, контакты) перечислены в TYPOGRAPH_SKIP_KEYS.
    """

    def render(self, request, data, *, response_status):
        return super().render(
            request, typograph_data(data), response_status=response_status,
        )
