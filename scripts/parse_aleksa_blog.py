#!/usr/bin/env python3
"""Парсер блога aleksa-dent.ru (Tilda) в JSON с HTML-контентом.

Забирает список статей из sitemap.xml, скачивает каждую страницу и вытаскивает
заголовок, описание и тело статьи. Фотографии пропускаются — их добавляют вручную.

Запуск:
    python3 scripts/parse_aleksa_blog.py
    python3 scripts/parse_aleksa_blog.py --no-cache --workers 8
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SITE = "https://aleksa-dent.ru"
SITEMAP_URL = f"{SITE}/sitemap.xml"
USER_AGENT = "Mozilla/5.0 (compatible; AlexaBlogParser/1.0)"

# Типы записей Tilda, из которых состоит статья.
REC_BREADCRUMBS = 758
REC_CONTACTS = 554
REC_HEADING = 33
REC_PARAGRAPH = 127
REC_SUMMARY = 248
REC_TABLE = 431
REC_CARDS = 847
REC_IMAGE = 3

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
SKIP_TAGS = {"script", "style", "template", "noscript", "iframe", "svg"}

# Теги, которые остаются в итоговом HTML. Остальные разворачиваются.
ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "a", "ul", "ol", "li",
    "h2", "h3", "h4", "blockquote", "table", "thead", "tbody",
    "tr", "th", "td", "sub", "sup",
}
WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
NEWLINES_RE = re.compile(r"\n{3,}")

PREVIEW_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ max-width: 760px; margin: 40px auto; padding: 0 16px;
            font: 18px/1.6 -apple-system, Segoe UI, Roboto, sans-serif; color: #222; }}
    h1 {{ font-size: 34px; line-height: 1.2; }}
    h2 {{ margin-top: 32px; font-size: 26px; }}
    h3 {{ margin-top: 24px; font-size: 21px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }}
    .descr {{ color: #555; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p class="descr">{description}</p>
  <hr>
{content}
</body>
</html>
"""


@dataclass
class Node:
    tag: str | None = None
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node | str"] = field(default_factory=list)

    @property
    def is_text(self) -> bool:
        return self.tag is None


class TreeBuilder(HTMLParser):
    """Терпимый к кривому HTML построитель дерева (stdlib-only)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="#root")
        self.stack: list[Node] = [self.root]

    def _append(self, node: Node | str) -> None:
        self.stack[-1].children.append(node)

    def handle_starttag(self, tag, attrs):
        node = Node(tag=tag.lower(), attrs={k.lower(): (v or "") for k, v in attrs})
        self._append(node)
        if node.tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag=tag.lower(), attrs={k.lower(): (v or "") for k, v in attrs})
        self._append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return
        # Непарный закрывающий тег игнорируем.

    def handle_data(self, data):
        self._append(data)


def parse_html(html: str) -> Node:
    builder = TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def walk(node: Node):
    """Обход в прямом порядке (документном порядке)."""
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from walk(child)


def text_content(node: Node) -> str:
    parts: list[str] = []

    def visit(n: Node) -> None:
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag in SKIP_TAGS:
                continue
            elif child.tag == "br":
                parts.append(" ")
            else:
                visit(child)

    visit(node)
    return WHITESPACE_RE.sub(" ", "".join(parts)).strip()


def find_by_attr(root: Node, name: str, value: str) -> Node | None:
    for node in walk(root):
        if node.attrs.get(name) == value:
            return node
    return None


def find_first_tag(root: Node, tags: set[str]) -> Node | None:
    for node in walk(root):
        if node.tag in tags:
            return node
    return None


def render_child(child: Node | str) -> str:
    if isinstance(child, str):
        return escape(child, quote=False).replace("\xa0", "&nbsp;")

    tag = child.tag
    if tag in SKIP_TAGS or tag == "img":
        return ""
    if tag == "br":
        return "<br>"
    if tag in {"b", "i"}:
        tag = {"b": "strong", "i": "em"}[tag]

    inner = "".join(render_child(item) for item in child.children)

    if tag == "a":
        href = child.attrs.get("href", "").strip()
        if href.startswith("/"):
            href = SITE + href
        if href and inner:
            return f'<a href="{escape(href, quote=True)}">{inner}</a>'
        return inner

    if tag in ALLOWED_TAGS:
        if tag in {"p", "li", "th", "td", "blockquote"} and not inner.strip():
            return ""
        return f"<{tag}>{inner}</{tag}>"
    # div, span и прочее — разворачиваем, оставляя содержимое.
    return inner


def sanitize(node: Node) -> str:
    """Внутренний HTML узла: без стилей/классов/картинок."""
    html = "".join(render_child(child) for child in node.children)
    html = re.sub(r"<p>\s*</p>", "", html)
    html = re.sub(r"<br>\s*<br>(\s*<br>)+", "<br><br>", html)
    return html.strip()


def list_items(node: Node) -> list[str] | None:
    """Если внутри узла список — вернуть пункты как HTML."""
    lst = find_first_tag(node, {"ul", "ol"})
    if not lst:
        return None
    items = []
    for item in walk(lst):
        if item.tag == "li":
            inner = sanitize(item)
            if inner:
                items.append(inner)
    return items or None


def split_table_cell(value: str) -> list[str]:
    return [part.strip() for part in value.split(";")]


def build_table(record: Node) -> str:
    header = ""
    rows_html: list[str] = []

    header_node = find_by_attr(record, "class", "t431__data-part1")
    body_node = find_by_attr(record, "class", "t431__data-part2")
    if header_node is not None:
        header = text_content(header_node)
    body = text_content(body_node) if body_node is not None else ""

    columns = split_table_cell(header) if header else []
    rows: list[list[str]] = []
    if body:
        for line in body.splitlines():
            line = line.strip()
            if line:
                rows.append(split_table_cell(line))

    if not rows and not columns:
        return ""

    width = max([len(columns)] + [len(row) for row in rows])
    if not any(columns):
        columns = []

    parts = ["<table>"]
    if columns:
        parts.append("<thead><tr>")
        for i in range(width):
            cell = columns[i] if i < len(columns) else ""
            parts.append(f"<th>{escape(cell)}</th>")
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in rows:
        parts.append("<tr>")
        for i in range(width):
            cell = row[i] if i < len(row) else ""
            parts.append(f"<td>{escape(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def build_cards(record: Node) -> str:
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}

    for node in walk(record):
        for field_name, value in node.attrs.items():
            if field_name != "field":
                continue
            match = re.match(r"li_(title|descr)__(\d+)$", value)
            if not match:
                continue
            kind, key = match.groups()
            cell_html = sanitize(node)
            if not cell_html:
                continue
            if kind == "title":
                titles[key] = cell_html
            else:
                descriptions[key] = cell_html

    keys = list(dict.fromkeys([*titles, *descriptions]))
    parts: list[str] = []
    for key in keys:
        title = titles.get(key)
        descr = descriptions.get(key)
        if title:
            parts.append(f"<h3>{title}</h3>")
        if descr:
            parts.append(f"<p>{descr}</p>")
    return "\n".join(parts)


BLOCK_TAGS = {
    "p", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "blockquote", "div",
}


def render_block_content(node: Node) -> list[str]:
    """Текст блока Tilda -> последовательность блочных HTML-элементов.

    Внутри одного текстового блока Tilda может лежать несколько списков,
    абзацев и «голый» текст между ними. Инлайновые куски собираем в <p>,
    чтобы на выходе был валидный HTML для CKEditor.
    """
    parts: list[str] = []
    inline: list[str] = []

    def flush_inline() -> None:
        html = "".join(inline).strip()
        inline.clear()
        if html:
            parts.append(f"<p>{html}</p>")

    for child in node.children:
        if isinstance(child, Node) and child.tag in BLOCK_TAGS and child.tag != "div":
            flush_inline()
            html = render_child(child)
            if html:
                parts.append(html)
        elif isinstance(child, Node) and child.tag == "div":
            # div-обёртку разворачиваем, но содержимое считаем блочным.
            flush_inline()
            parts.extend(render_block_content(child))
        else:
            html = render_child(child)
            if html:
                inline.append(html)

    flush_inline()
    return parts


ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def normalize_html(html: str) -> str:
    html = ZERO_WIDTH_RE.sub("", html)
    html = html.replace("\t", " ")
    html = NEWLINES_RE.sub("\n\n", html)
    html = re.sub(r"\s+</p>", "</p>", html)
    html = re.sub(r"<p>\s+", "<p>", html)
    return html.strip()


def extract_post(html: str, url: str, lastmod: str | None) -> dict:
    root = parse_html(html)
    slug = url.rstrip("/").rsplit("/", 1)[-1]

    og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', html)
    og_descr = re.search(
        r'<meta[^>]+(?:property|name)="(?:og:description|description)"[^>]+content="([^"]*)"',
        html,
    )

    records: list[Node] = []
    for node in walk(root):
        if node.tag == "div" and re.fullmatch(r"rec\d+", node.attrs.get("id", "")):
            records.append(node)

    type_of = {
        id(node): int(node.attrs.get("data-record-type", "0"))
        for node in records
    }
    start = next(
        (i for i, node in enumerate(records) if type_of[id(node)] == REC_BREADCRUMBS),
        None,
    )
    if start is None:
        raise ValueError("не найден блок хлебных крошек (758)")
    end = next(
        (
            i
            for i, node in enumerate(records)
            if i > start and type_of[id(node)] == REC_CONTACTS
        ),
        len(records),
    )

    title = ""
    description = ""
    blocks: list[str] = []
    list_buffer: dict[str, list[str]] = {}

    def flush_list() -> None:
        nonlocal list_buffer
        if not list_buffer:
            return
        for tag, items in list_buffer.items():
            if items:
                inner = "".join(f"<li>{item}</li>" for item in items)
                blocks.append(f"<{tag}>{inner}</{tag}>")
        list_buffer = {}

    for record in records[start + 1 : end]:
        record_type = type_of[id(record)]

        if record_type == REC_IMAGE:
            continue

        if record_type == REC_TABLE:
            flush_list()
            table = build_table(record)
            if table:
                blocks.append(table)
            continue

        if record_type == REC_CARDS:
            flush_list()
            cards = build_cards(record)
            if cards:
                blocks.append(cards)
            continue

        if record_type == REC_HEADING:
            heading = find_first_tag(record, {"h1", "h2", "h3", "h4", "h5", "h6"})
            if heading is None:
                continue
            heading_text = text_content(heading)
            if not title:
                title = heading_text
            inner = sanitize(heading)
            if not inner:
                continue
            items = list_items(heading)
            if items:
                list_buffer.setdefault("ul", []).extend(items)
                continue
            flush_list()
            if heading_text and heading_text == title and not blocks:
                # Первый h1 дублирует title — в контенте он не нужен.
                continue
            tag = "h3" if heading.tag in {"h3", "h4", "h5", "h6"} else "h2"
            blocks.append(f"<{tag}>{inner}</{tag}>")
            continue

        # Абзацы (127), финальный блок (248) и прочие текстовые блоки.
        text_node = find_by_attr(record, "field", "text")
        if text_node is None:
            text_node = find_by_attr(record, "field", "title")
        if text_node is None:
            continue

        if not description:
            description = text_content(text_node)

        flush_list()
        blocks.extend(render_block_content(text_node))

    flush_list()

    content = normalize_html("\n".join(blocks))

    if not description and og_descr:
        description = og_descr.group(1)
    description = ZERO_WIDTH_RE.sub("", description)
    description = WHITESPACE_RE.sub(" ", description.replace("\n", " ")).strip()
    description = re.sub(r"\s+", " ", description)

    if not title and og_title:
        title = og_title.group(1)
    title = WHITESPACE_RE.sub(" ", title).strip()

    if not title:
        raise ValueError("не найден заголовок")
    if not content:
        raise ValueError("пустой контент")

    return {
        "title": title,
        "slug": slug,
        "description": description,
        "content": content,
        "source_url": url,
        "source_lastmod": lastmod,
    }


def ssl_context() -> ssl.SSLContext:
    """Контекст с рабочим CA-бандлом.

    У python.org-сборок на macOS часто нет системных корневых сертификатов,
    поэтому пробуем certifi и типовые пути, а в крайнем случае — системный.
    """
    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 - certifi опционален
        pass

    candidates = (
        "/etc/ssl/cert.pem",
        "/opt/homebrew/etc/openssl@3/cert.pem",
        "/usr/local/etc/openssl@3/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ssl.create_default_context(cafile=candidate)
            except ssl.SSLError:
                continue
    return ssl.create_default_context()


_SSL_CONTEXT = ssl_context()


def fetch(url: str, cache_dir: Path | None) -> str:
    if cache_dir is not None:
        cache_file = cache_dir / (re.sub(r"[^a-zA-Z0-9._-]+", "_", url) + ".html")
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(
        request, timeout=30, context=_SSL_CONTEXT
    ) as response:
        data = response.read().decode("utf-8", errors="replace")
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(data, encoding="utf-8")
    return data


def read_sitemap() -> list[tuple[str, str | None]]:
    xml = fetch(SITEMAP_URL, None)
    entries: list[tuple[str, str | None]] = []
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block, re.S)
        if not loc:
            continue
        url = loc.group(1).strip()
        if not re.search(r"/blog/[^/]+$", url):
            continue
        lastmod_match = re.search(r"<lastmod>(.*?)</lastmod>", block, re.S)
        entries.append((url, lastmod_match.group(1).strip() if lastmod_match else None))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "data" / "aleksa_blog",
        help="куда писать JSON (по умолчанию data/aleksa_blog)",
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="параллельных загрузок (по умолчанию 8)"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="не использовать кеш загрузок"
    )
    args = parser.parse_args()

    cache_dir: Path | None = None
    if not args.no_cache:
        cache_dir = Path(tempfile.gettempdir()) / "aleksa_blog_cache"

    print(f"Читаю sitemap: {SITEMAP_URL}")
    entries = read_sitemap()
    if not entries:
        print("В sitemap не найдено статей блога.", file=sys.stderr)
        return 1
    print(f"Найдено статей: {len(entries)}")

    def load(entry: tuple[str, str | None]) -> tuple[tuple[str, str | None], str]:
        url, lastmod = entry
        return entry, fetch(url, cache_dir)

    posts: list[dict] = []
    errors: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for entry, html in pool.map(load, entries):
            url, lastmod = entry
            try:
                posts.append(extract_post(html, url, lastmod))
            except Exception as exc:  # noqa: BLE001 - нужен отчёт по каждой статье
                errors.append((url, str(exc)))

    posts.sort(key=lambda post: post["title"])

    output: Path = args.output
    posts_dir = output / "posts"
    html_dir = output / "html"
    for directory in (posts_dir, html_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    for post in posts:
        (posts_dir / f"{post['slug']}.json").write_text(
            json.dumps(post, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (html_dir / f"{post['slug']}.html").write_text(
            PREVIEW_TEMPLATE.format(
                title=escape(post["title"]),
                description=escape(post["description"]),
                content=post["content"],
            ),
            encoding="utf-8",
        )

    (output / "posts.json").write_text(
        json.dumps(posts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    total_chars = sum(len(post["content"]) for post in posts)
    print(f"Готово: {len(posts)} статей -> {output / 'posts.json'}")
    print(f"По одной статье на файл: {posts_dir}/")
    print(f"HTML для предпросмотра:   {html_dir}/")
    print(f"Всего символов контента: {total_chars:,}".replace(",", " "))
    if errors:
        print(f"\nОшибки ({len(errors)}):", file=sys.stderr)
        for url, message in errors:
            print(f"  {url}: {message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
