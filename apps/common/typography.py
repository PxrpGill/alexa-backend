"""Локальная типографика для русских текстов (офлайн-аналог типографа Лебедева).

Реализует основные правила русской типографики:
ёлочки для кавычек, длинное тире, неразрывные пробелы после коротких
предлогов, неразрывные пробелы перед % и №, многоточие и пр.

Дополнительно typograph_html() убирает style-атрибуты из HTML и применяет
типографику только к текстовым узлам, не трогая разметку.
"""

import re
from html.parser import HTMLParser

NBSP = '\u00A0'

_GLUE_WORDS = (
    'в', 'к', 'с', 'у', 'о', 'и', 'а', 'я',
    'но', 'до', 'за', 'на', 'по', 'со', 'из', 'об', 'от', 'не',
)
_ONE_LETTER_RE = re.compile(
    r'\b(' + '|'.join(_GLUE_WORDS) + r')\s+(?=\S)', re.IGNORECASE,
)

_STYLE_ATTR_RE = re.compile(
    r"""\s+style\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE,
)
_BARE_STYLE_ATTR_RE = re.compile(r'\s+style(?=\s|>)', re.IGNORECASE)


_QUOTE_OPENER_AFTER = set('«„([—')


def _process_quotes(text):
    """Нормализует кавычки по правилам русской типографики.

    - Прямые двойные кавычки «"» становятся «ёлочками».
    - Внешний уровень — «ёлочки» («»), вложенный — „лапки" („... ").
    - Уже проставленные «» и „... " перенумеровываются по уровню вложенности.
    """
    out = []
    depth = 0
    for i, ch in enumerate(text):
        if ch == '"':
            prev = text[i - 1] if i > 0 else ''
            is_open = (not prev) or prev.isspace() or prev in _QUOTE_OPENER_AFTER
            if is_open or depth == 0:
                out.append('«' if depth % 2 == 0 else '„')
                depth += 1
            else:
                depth -= 1
                out.append('»' if depth % 2 == 0 else '"')
        elif ch in ('«', '„'):
            out.append('«' if depth % 2 == 0 else '„')
            depth += 1
        elif ch == '»':
            if depth == 0:
                out.append('»')
            else:
                depth -= 1
                out.append('»' if depth % 2 == 0 else '"')
        else:
            out.append(ch)
    return ''.join(out)


def typograph_text(text, html_entities=False):
    """Применяет основные правила русской типографики к обычному тексту.

    При html_entities=True неразрывный пробел, длинное тире и многоточие
    отдаются в виде HTML-entity (&nbsp;, &mdash;, &hellip;) — удобно для
    встраивания результата в HTML.
    """
    if not text:
        return text

    # 1. Схлопнуть подряд идущие пробелы/табы (но не неразрывные пробелы).
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # 2. Убрать пробел перед точкой и запятой.
    text = re.sub(r'\s+([.,])', r'\1', text)
    # 3. Кавычки: «ёлочки», вложенные — „лапки".
    text = _process_quotes(text)
    # 4. Троеточие.
    text = re.sub(r'\.{3,}', '…', text)
    # 5. Тире: « - » -> « — », двойной дефис -> длинное тире.
    text = re.sub(r'(?<=\s)-(?=\s)', '—', text)
    text = re.sub(r'-{2,}', '—', text)
    # 5a. Неразрывный пробел перед тире (тире приклеивается к слову слева).
    text = re.sub(r'(?<=\S)\s+(?=—)', NBSP, text)
    # 6. Убрать пробелы у скобок и ёлочек внутри.
    text = re.sub(r'\s+(?=[\)\]»])', '', text)
    text = re.sub(r'(?<=[\(\[«])\s+', '', text)
    # 7. Неразрывный пробел после коротких предлогов и союзов.
    text = _ONE_LETTER_RE.sub(r'\1' + NBSP, text)
    # 8. Неразрывный пробел перед % и ‰.
    text = re.sub(r'(?<=\S)\s+(?=[%‰])', NBSP, text)
    # 9. «№» приклеивается к числу неразрывным пробелом.
    text = re.sub(r'№\s*(?=\d)', '№' + NBSP, text)
    # 10. Неразрывный пробел перед «?» и «!».
    text = re.sub(r'(?<=\S)\s+(?=[?!])', NBSP, text)
    if html_entities:
        text = text.replace(NBSP, '&nbsp;')
        text = text.replace('—', '&mdash;')
        text = text.replace('…', '&hellip;')
    return text


def _strip_style(tag_text):
    """Убирает style-атрибут (вместе с окружающими пробелами) из тега."""
    tag_text = _STYLE_ATTR_RE.sub('', tag_text)
    tag_text = _BARE_STYLE_ATTR_RE.sub('', tag_text)
    return tag_text


class _HTMLTypographParser(HTMLParser):
    """Пересобирает HTML, применяя типографику к тексту и удаляя style.

    entity-ссылки (например &nbsp;) сохраняются как есть.
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self._skip_style_block = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'style':
            self._skip_style_block = True
            return
        if self._skip_style_block:
            return
        raw = self.get_starttag_text()
        self.parts.append(_strip_style(raw) if raw else '<%s>' % tag)

    def handle_startendtag(self, tag, attrs):
        if self._skip_style_block:
            return
        raw = self.get_starttag_text()
        self.parts.append(_strip_style(raw) if raw else '<%s/>' % tag)

    def handle_endtag(self, tag):
        if tag.lower() == 'style':
            self._skip_style_block = False
            return
        if self._skip_style_block:
            return
        self.parts.append('</%s>' % tag)

    def handle_data(self, data):
        if self._skip_style_block:
            return
        self.parts.append(typograph_text(data, html_entities=True))

    def handle_entityref(self, name):
        if name == 'mdash' and self.parts:
            last = self.parts[-1]
            stripped = last.rstrip(' \t\n\r')
            if stripped != last:
                self.parts[-1] = stripped + '&nbsp;'
        self.parts.append('&%s;' % name)

    def handle_charref(self, name):
        self.parts.append('&#%s;' % name)

    def handle_comment(self, data):
        self.parts.append('<!--%s-->' % data)

    def handle_decl(self, decl):
        self.parts.append('<!%s>' % decl)

    def handle_pi(self, data):
        self.parts.append('<?%s>' % data)

    def handle_cdata(self, data):
        self.parts.append('<![CDATA[%s]]>' % data)


def typograph_html(html):
    """Типографирует текстовые узлы HTML и удаляет все style-атрибуты.

    Разметка сохраняется как есть. В случае ошибки разбора возвращается
    исходный HTML, чтобы никогда не потерять контент при сохранении.
    """
    if not html:
        return html
    try:
        parser = _HTMLTypographParser()
        parser.feed(html)
        parser.close()
        return ''.join(parser.parts)
    except Exception:
        return html
