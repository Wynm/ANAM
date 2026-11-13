"""جامع RSS/Atom عام وقابل للتوسعة — يعمل مع أي موجز إنترنت مجاني.

افتراضياً يلتقط آخر أخبار Hacker News (الأكثر تداولاً بين المطورين).
أضف أي موجز RSS/Atom في anam_config.json ضمن rss.feeds وسيُدمج تلقائياً.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from ..http import HttpError, get_text
from ..models import Item
from .base import Source

_TAG = re.compile(r"<[^>]+>")


class RssSource(Source):
    name = "rss"

    def __init__(self, cfg: dict):
        rss = cfg.get("rss", {})
        self.feeds: list[str] = rss.get("feeds", [])
        self.max_per_feed: int = int(rss.get("max_items_per_feed", 20))

    def collect(self, limit: int = 100) -> list[Item]:
        items: list[Item] = []
        for feed in self.feeds:
            try:
                body = get_text(feed, timeout=15)
            except HttpError as e:
                print(f"[rss] تعذر جلب {feed}: {e}")
                continue
            items.extend(self._parse(body, feed)[: self.max_per_feed])
            if len(items) >= limit:
                break
        return items[:limit]

    def _parse(self, body: str, feed: str) -> list[Item]:
        out: list[Item] = []
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            print(f"[rss] XML غير صالح في {feed}: {e}")
            return out

        entries = root.iter("item")  # RSS 2.0
        is_atom = False
        sample = list(entries)
        if not sample:
            is_atom = True
            sample = list(root.iter("{http://www.w3.org/2005/Atom}entry"))

        for e in sample:
            if is_atom:
                title = _text(e, "{http://www.w3.org/2005/Atom}title")
                link_el = e.find("{http://www.w3.org/2005/Atom}link")
                link = (link_el.get("href") if link_el is not None else "") or ""
                summary = _text(e, "{http://www.w3.org/2005/Atom}summary") or _text(e, "{http://www.w3.org/2005/Atom}content")
                created = _text(e, "{http://www.w3.org/2005/Atom}updated") or _text(e, "{http://www.w3.org/2005/Atom}published")
            else:
                title = _text(e, "title")
                link = _text(e, "link")
                summary = _text(e, "description")
                created = _text(e, "pubDate")
            title = _clean(title)
            if not title:
                continue
            out.append(Item(
                source="rss",
                kind="article",
                name=title[:200],
                url=link or feed,
                description=_clean(summary)[:1000],
                created_at=created or datetime.now(timezone.utc).isoformat(),
                updated_at=created or "",
                raw={"feed": feed},
            ))
        return out


def _text(el, tag):
    node = el.find(tag)
    return (node.text or "") if node is not None else ""


def _clean(s: str) -> str:
    return _TAG.sub("", s or "").replace("\n", " ").strip()
