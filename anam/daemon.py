"""الوضع الذاتي — يشغّل ANAM بدون توقف وبدون أي خدمة مدفوعة.

حلقة بسيطة وقوية: كل `interval_minutes` تجمع ← تحلل ← تصنف ← تبلغ.
أي خطأ عابر لا يوقف العملية؛ يُسجّل ويُستأنف. الإيقاف: Ctrl+C أو إشارة.
"""
from __future__ import annotations

import datetime as _dt
import json
import time
from pathlib import Path

from .analyze.scoring import evaluate
from .config import load_config
from .report import build_report
from .sources import build_sources
from .storage import Store


def one_cycle(cfg: dict, mode: str) -> tuple[int, int]:
    store = Store(cfg["storage"]["db_path"])
    try:
        items = []
        for src in build_sources(cfg):
            try:
                items.extend(src.collect(limit=int(cfg["filters"].get("max_items_full_mode", 300))))
            except Exception as e:
                print(f"[daemon] مصدر {src.name} فشل هذه الدورة: {e}")
        # خزّن ثم قيّم (سرعة الصعود تقارن بأحدث لقطتين)
        for it in items:
            store.upsert_item(it)
        evaluated = [(it, evaluate(it, store, cfg, mode)) for it in items]
        if mode == "full":
            kept = evaluated[: int(cfg["filters"].get("max_items_full_mode", 300))]
        else:
            kept = [p for p in evaluated if p[1]["keep"]]
            kept.sort(key=lambda p: p[1].get("hype_score", 0), reverse=True)
            kept = kept[: int(cfg["filters"].get("normal_max_items", 50))]
        build_report(kept, mode, cfg["reports"]["output_dir"])
        store.record_run(mode, len(items), len(kept))
        return len(items), len(kept)
    finally:
        store.close()


def run_forever(cfg_path: str | None, mode: str | None, interval_minutes: float | None) -> None:
    cfg = load_config(cfg_path)
    mode = mode or cfg.get("mode", "normal")
    interval = float(interval_minutes if interval_minutes is not None
                     else cfg.get("daemon", {}).get("interval_minutes", 360))
    heartbeat = Path("data/heartbeat.json")
    print(f"[daemon] ANAM يعمل — الوضع={mode} — الدورة كل {interval:.0f} دقيقة. أوقف بـ Ctrl+C.")
    while True:
        started = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            collected, kept = one_cycle(cfg, mode)
            print(f"[daemon] {started} — التقط {collected}، أُبقي {kept} في التقرير.")
            heartbeat.parent.mkdir(parents=True, exist_ok=True)
            heartbeat.write_text(json.dumps(
                {"last_run": started, "collected": collected, "kept": kept, "mode": mode},
                ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[daemon] {started} — خطأ في الدورة (ستُعاد المحاولة): {e}")
        time.sleep(max(interval, 1.0) * 60)
