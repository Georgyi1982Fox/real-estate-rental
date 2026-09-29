"""Очистка текста объявлений (TASK-019)."""

import html
import re

_BREAK_RE = re.compile(r"<\s*br\s*/?\s*>|<\s*/\s*p\s*>|<\s*p[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]{0,200}>")


def html_to_text(text: str) -> str:
    """HTML сайта (``<br />``, ``<p>``, ``&amp;``) → обычный текст с переносами строк."""
    if not text or ("<" not in text and "&" not in text):
        return text
    text = _BREAK_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    return html.unescape(text)
