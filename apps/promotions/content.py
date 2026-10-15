import re

# CKEditor пишет в пустое поле разметку вида "<p><br></p>" или "<p>&nbsp;</p>",
# поэтому пустоту нужно проверять после вычистки тегов и пробелов.
_EMPTY_MARKUP_RE = re.compile(r"<[^>]*>|&nbsp;|&#160;|\s", re.IGNORECASE)
_MEDIA_TAG_RE = re.compile(r"<(img|iframe|video|audio)\b", re.IGNORECASE)


def has_content(value):
    """Есть ли в значении осмысленный контент (медиа или текст без разметки)."""
    if not value:
        return False
    if isinstance(value, str):
        if _MEDIA_TAG_RE.search(value):
            return True
        return bool(_EMPTY_MARKUP_RE.sub("", value).strip())
    return bool(value)