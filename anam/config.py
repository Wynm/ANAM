"""تحميل الإعدادات: قيم افتراضية + ملف anam_config.json (إن وُجد)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "mode": "normal",
    "github": {
        "enabled": True,
        "queries": [
            "created:>={since} stars:>=10",
            "pushed:>={since} stars:>=50",
            "created:>={since} topic:ai",
            "created:>={since} topic:automation",
            "created:>={since} topic:saas",
        ],
        "per_page": 25,
        "token_env": "GITHUB_TOKEN",
    },
    "npm": {
        "enabled": True,
        "keywords": ["ai agent", "llm", "automation", "saas",
                     "analytics", "trading", "rag", "workflow"],
        "per_query": 10,
    },
    "rss": {"enabled": True, "feeds": ["https://news.ycombinator.com/rss"],
            "max_items_per_feed": 20},
    "filters": {
        "normal_min_stars": 500,
        "normal_min_star_velocity_per_day": 25.0,
        "normal_recent_days": 45,
        "npm_min_weekly_downloads": 50000,
        "normal_max_items": 50,
        "max_items_full_mode": 300,
    },
    "storage": {"db_path": "data/anam.db"},
    "reports": {"output_dir": "reports", "language": "ar"},
    "daemon": {"interval_minutes": 360},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | os.PathLike | None = None) -> dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULTS))  # نسخة عميقة
    candidate = Path(path) if path else Path("anam_config.json")
    if candidate.exists():
        try:
            user_cfg = json.loads(candidate.read_text(encoding="utf-8"))
            cfg = _deep_merge(cfg, user_cfg)
        except Exception as e:
            print(f"[تحذير] تعذر قراءة {candidate}: {e} — سيتم استخدام الإعدادات الافتراضية")
    return cfg
