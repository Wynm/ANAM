"""نماذج البيانات الموحدة لكل المصادر."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Item:
    """عنصر واحد جديد (مستودع / حزمة / مقال) تم التقاطه من الويب."""

    source: str                    # github | npm | rss
    kind: str                      # repo | package | article
    name: str
    url: str
    uid: str = ""                  # معرّف فريد: source:name
    author: str = ""
    description: str = ""
    language: str = ""
    stars: int = 0
    forks: int = 0
    issues: int = 0
    downloads_week: Optional[int] = None
    license: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    topics: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.uid:
            self.uid = f"{self.source}:{self.name.lower()}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Item":
        return Item(**{k: v for k, v in d.items() if k in Item.__dataclass_fields__})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
