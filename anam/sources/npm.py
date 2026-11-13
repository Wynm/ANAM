"""جامع npm — حزم حديثة في مسارات الذكاء الاصطناعي والأتمتة والـSaaS.

يستخدم واجهة البحث العامة لسجل npm (مجانية وبدون مفتاح)، وتأتي
إحصائيات التحميل الأسبوعية والمعتمِدات (dependents) ضمن نتيجة البحث نفسها.
"""
from __future__ import annotations

from urllib.parse import quote

from ..http import HttpError, get_json
from ..models import Item
from .base import Source

API = "https://registry.npmjs.org/-/v1/search"


class NpmSource(Source):
    name = "npm"

    def __init__(self, cfg: dict):
        npm = cfg.get("npm", {})
        self.keywords: list[str] = npm.get("keywords", [])
        self.per_query: int = int(npm.get("per_query", 10))

    def collect(self, limit: int = 100) -> list[Item]:
        seen: dict[str, Item] = {}
        for kw in self.keywords:
            for sort in ("date", "popularity"):
                url = f"{API}?text={quote('keywords:' + kw)}&size={self.per_query}&sort={sort}"
                try:
                    data = get_json(url)
                except HttpError as e:
                    print(f"[npm] تعذر البحث عن «{kw}» ({sort}): {e}")
                    continue
                for obj in data.get("objects", []):
                    pkg = obj.get("package") or {}
                    name = pkg.get("name") or ""
                    if not name or name.lower() in seen:
                        continue
                    dl = (obj.get("downloads") or {}).get("weekly")
                    links = pkg.get("links") or {}
                    seen[name.lower()] = Item(
                        source="npm",
                        kind="package",
                        name=name,
                        url=links.get("npm") or f"https://www.npmjs.com/package/{name}",
                        author=_author(pkg.get("publisher") or pkg.get("author")),
                        description=pkg.get("description") or "",
                        language="JavaScript/TypeScript",
                        downloads_week=int(dl) if dl is not None else None,
                        license=(pkg.get("license") or None),
                        created_at=pkg.get("date") or "",
                        updated_at=pkg.get("date") or "",
                        topics=list(pkg.get("keywords") or []),
                        raw={"version": pkg.get("version", ""),
                             "dependents": obj.get("dependents", ""),
                             "search_score": obj.get("searchScore", 0)},
                    )
                    if len(seen) >= limit:
                        break
                if len(seen) >= limit:
                    break
            if len(seen) >= limit:
                break
        return list(seen.values())


def _author(a) -> str:
    if isinstance(a, dict):
        return a.get("username") or a.get("name") or ""
    return str(a or "")
