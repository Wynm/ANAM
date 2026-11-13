"""التخزين الدائم — SQLite محلي، مجاني، ويعمل بدون خادم.

يخزن العناصر ولقطات المؤشرات عبر الزمن حتى نستطيع قياس «سرعة الصعود»
(عدد النجوم/اليوم بين كل تشغيل وتشغيل) وهو أساس كاشف الضجة في الوضع العادي.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Optional

from .models import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    uid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    data TEXT NOT NULL,            -- JSON كامل للعنصر
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    uid TEXT NOT NULL,
    ts REAL NOT NULL,
    stars INTEGER NOT NULL DEFAULT 0,
    forks INTEGER NOT NULL DEFAULT 0,
    issues INTEGER NOT NULL DEFAULT 0,
    downloads_week INTEGER
);
CREATE INDEX IF NOT EXISTS idx_snap_uid ON snapshots(uid, ts);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    mode TEXT NOT NULL,
    collected INTEGER NOT NULL,
    kept INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # ---------- الكتابة ----------
    def upsert_item(self, item: Item) -> None:
        now = time.time()
        self.db.execute(
            """INSERT INTO items(uid, source, kind, name, url, data, first_seen, last_seen)
               VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET
                 data=excluded.data, last_seen=excluded.last_seen""",
            (item.uid, item.source, item.kind, item.name, item.url,
             item.to_json(), now, now),
        )
        self.db.execute(
            """INSERT INTO snapshots(uid, ts, stars, forks, issues, downloads_week)
               VALUES(?,?,?,?,?,?)""",
            (item.uid, now, item.stars, item.forks, item.issues, item.downloads_week),
        )
        self.db.commit()

    def record_run(self, mode: str, collected: int, kept: int) -> None:
        self.db.execute(
            "INSERT INTO runs(ts, mode, collected, kept) VALUES(?,?,?,?)",
            (time.time(), mode, collected, kept),
        )
        self.db.commit()

    # ---------- القراءة ----------
    def previous_snapshot(self, uid: str) -> Optional[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM snapshots WHERE uid=? ORDER BY ts DESC LIMIT 1 OFFSET 1",
            (uid,),
        ).fetchone()

    def velocity_pair(self, uid: str):
        """أحدث لقطتين: (الأحدث، التي قبلها) — أساس قياس سرعة الصعود."""
        rows = self.db.execute(
            "SELECT * FROM snapshots WHERE uid=? ORDER BY ts DESC LIMIT 2", (uid,)
        ).fetchall()
        if len(rows) < 2:
            return (rows[0] if rows else None), None
        return rows[0], rows[1]

    def snapshot_count(self, uid: str) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) c FROM snapshots WHERE uid=?", (uid,)
        ).fetchone()
        return int(row["c"])

    def first_seen(self, uid: str) -> Optional[float]:
        row = self.db.execute(
            "SELECT first_seen FROM items WHERE uid=?", (uid,)
        ).fetchone()
        return float(row["first_seen"]) if row else None

    def all_items(self) -> list[Item]:
        rows = self.db.execute("SELECT data FROM items ORDER BY last_seen DESC").fetchall()
        out = []
        for r in rows:
            try:
                out.append(Item.from_dict(json.loads(r["data"])))
            except Exception:
                continue
        return out

    def stats(self) -> dict:
        items = self.db.execute("SELECT COUNT(*) c FROM items").fetchone()["c"]
        snaps = self.db.execute("SELECT COUNT(*) c FROM snapshots").fetchone()["c"]
        runs = self.db.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"]
        return {"items": items, "snapshots": snaps, "runs": runs}
