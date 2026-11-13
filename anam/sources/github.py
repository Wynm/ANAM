"""جامع GitHub — المصدر الأغنى بالمستجدات التقنية.

يستخدم GitHub Search API (مجاني) للبحث عن المستودعات المنشأة/المدفوعة
حديثاً. التوكن اختياري (GITHUB_TOKEN) لرفع الحد من 10 إلى 30 طلباً/دقيقة.
"""
from __future__ import annotations

import datetime as _dt
from urllib.parse import quote

from ..http import HttpError, get_json, github_token
from ..models import Item
from .base import Source

API = "https://api.github.com/search/repositories"


class GitHubSource(Source):
    name = "github"

    def __init__(self, cfg: dict):
        gh = cfg.get("github", {})
        self.queries: list[str] = gh.get("queries", [])
        self.per_page: int = int(gh.get("per_page", 25))
        self.token = github_token(gh.get("token_env", "GITHUB_TOKEN"))
        self.lookback_days: int = int(cfg.get("filters", {}).get("normal_recent_days", 45))

    def collect(self, limit: int = 100) -> list[Item]:
        since = (_dt.date.today() - _dt.timedelta(days=self.lookback_days)).isoformat()
        seen: dict[str, Item] = {}
        for q in self.queries:
            query = q.replace("{since}", since)
            url = f"{API}?q={quote(query)}&sort=stars&order=desc&per_page={self.per_page}"
            try:
                data = get_json(url, token=self.token)
            except HttpError as e:
                print(f"[github] تعذر التنفيذ للاستعلام «{query}»: {e}")
                continue
            for r in data.get("items", []):
                full = r.get("full_name", "")
                if not full or full.lower() in seen:
                    continue
                lic = r.get("license") or {}
                seen[full.lower()] = Item(
                    source="github",
                    kind="repo",
                    name=full,
                    url=r.get("html_url") or f"https://github.com/{full}",
                    author=(r.get("owner") or {}).get("login", ""),
                    description=r.get("description") or "",
                    language=r.get("language") or "",
                    stars=int(r.get("stargazers_count", 0)),
                    forks=int(r.get("forks_count", 0)),
                    issues=int(r.get("open_issues_count", 0)),
                    license=lic.get("spdx_id") if isinstance(lic, dict) else None,
                    created_at=r.get("created_at") or "",
                    updated_at=r.get("pushed_at") or r.get("updated_at") or "",
                    topics=list(r.get("topics") or []),
                    raw={"archived": bool(r.get("archived")),
                         "watchers": r.get("watchers_count", 0),
                         "size": r.get("size", 0),
                         "default_branch": r.get("default_branch", "")},
                )
                if len(seen) >= limit:
                    break
            if len(seen) >= limit:
                break
        return list(seen.values())
