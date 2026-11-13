"""واجهة ANAM للسطر — كل ما تحتاجه في أمر واحد.

الأوامر:
  scan        التقط المستجدات الآن وولّد تقريراً (الوضع العادي افتراضياً)
  scan --mode full   الوضع التام: كل ما وُجد بدون فلترة الضجة
  report      أعد توليد التقرير من كل ما خزّنه ANAM سابقاً (بدون شبكة)
  diagnose    شخّص أي مستودع/حزمة/رابط/كلمة مفتاحية — بدون أي عتبات
  self-improve  اجعل ANAM يقترح تحسين نفسه من المستجدات الملتقطة
  daemon      شغّل ANAM بلا توقف (كل N دقيقة) — مجاني بالكامل
  status      إحصائيات الذاكرة المحلية
"""
from __future__ import annotations

import argparse
import sys

from .analyze.scoring import evaluate
from .config import load_config
from .diagnose import diagnose
from .report import build_report
from .selfimprove import suggest
from .sources import build_sources
from .storage import Store


def _cmd_scan(args) -> int:
    cfg = load_config(args.config)
    mode = args.mode or cfg.get("mode", "normal")
    store = Store(cfg["storage"]["db_path"])
    print(f"[anam] المسح — الوضع: {mode}")
    items = []
    try:
        for src in build_sources(cfg):
            try:
                got = src.collect(limit=int(cfg["filters"].get("max_items_full_mode", 300)))
                print(f"[anam] المصدر {src.name}: {len(got)} عنصر")
                items.extend(got)
            except Exception as e:
                print(f"[anam] المصدر {src.name} فشل: {e}")
        for it in items:
            store.upsert_item(it)
        evaluated = [(it, evaluate(it, store, cfg, mode)) for it in items]
        kept = evaluated if mode == "full" else [p for p in evaluated if p[1]["keep"]]
        kept.sort(key=lambda p: p[1].get("hype_score", 0), reverse=True)
        if mode != "full":
            kept = kept[: int(cfg["filters"].get("normal_max_items", 50))]
        kept = kept[: int(cfg["filters"].get("max_items_full_mode", 300))] if mode == "full" else kept
        md_path, json_path = build_report(kept, mode, cfg["reports"]["output_dir"])
        store.record_run(mode, len(items), len(kept))
        print(f"[anam] ✅ التقط {len(items)} — أُبقي {len(kept)} في التقرير ({mode})")
        print(f"[anam] 📄 {md_path}")
        print(f"[anam] 🧾 {json_path}")
        return 0
    finally:
        store.close()


def _cmd_report(args) -> int:
    cfg = load_config(args.config)
    mode = args.mode or cfg.get("mode", "normal")
    store = Store(cfg["storage"]["db_path"])
    try:
        items = store.all_items()
        evaluated = [(it, evaluate(it, store, cfg, mode)) for it in items]
        kept = evaluated if mode == "full" else [p for p in evaluated if p[1]["keep"]]
        kept.sort(key=lambda p: p[1].get("hype_score", 0), reverse=True)
        if mode != "full":
            kept = kept[: int(cfg["filters"].get("normal_max_items", 50))]
        md_path, json_path = build_report(kept, mode, cfg["reports"]["output_dir"])
        print(f"[anam] ✅ تقرير من الذاكرة: {len(kept)} عنصر ({mode})")
        print(f"[anam] 📄 {md_path}")
        return 0
    finally:
        store.close()


def _cmd_diagnose(args) -> int:
    cfg = load_config(args.config)
    text = diagnose(args.query, cfg["reports"]["output_dir"], cfg)
    print(text)
    return 0


def _cmd_self_improve(args) -> int:
    cfg = load_config(args.config)
    store = Store(cfg["storage"]["db_path"])
    try:
        items = store.all_items()
        path = suggest(items, cfg["reports"]["output_dir"])
        print(f"[anam] ✅ خطة تحسين ذاتية: {path}")
        return 0
    finally:
        store.close()


def _cmd_daemon(args) -> int:
    from .daemon import run_forever
    run_forever(args.config, args.mode, args.interval_minutes)
    return 0


def _cmd_status(args) -> int:
    cfg = load_config(args.config)
    store = Store(cfg["storage"]["db_path"])
    try:
        s = store.stats()
        print(f"[anam] العناصر المخزنة: {s['items']} | اللقطات: {s['snapshots']} | التشغيلات: {s['runs']}")
        return 0
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="anam", description="ANAM — منصة ذكاء المستجدات (عربية، مجانية)")
    p.add_argument("--config", default=None, help="مسار anam_config.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="التقط المستجدات وولّد تقريراً")
    s.add_argument("--mode", choices=["normal", "full"], default=None,
                   help="normal = الضجة فقط (افتراضي) | full = كل شيء بدون فلترة")
    s.set_defaults(func=_cmd_scan)

    r = sub.add_parser("report", help="ولّد تقريراً من الذاكرة المحلية")
    r.add_argument("--mode", choices=["normal", "full"], default=None)
    r.set_defaults(func=_cmd_report)

    d = sub.add_parser("diagnose", help="شخّص أي مستودع/حزمة/رابط/كلمة مفتاحية")
    d.add_argument("query", help="مثال: facebook/react | @scope/pkg | npm:lodash | https://github.com/o/r | 'ai agents'")
    d.set_defaults(func=_cmd_diagnose)

    si = sub.add_parser("self-improve", help="اجعل ANAM يقترح تحسين نفسه")
    si.set_defaults(func=_cmd_self_improve)

    dm = sub.add_parser("daemon", help="شغّل ANAM بلا توقف")
    dm.add_argument("--mode", choices=["normal", "full"], default=None)
    dm.add_argument("--interval-minutes", type=float, default=None)
    dm.set_defaults(func=_cmd_daemon)

    st = sub.add_parser("status", help="إحصائيات الذاكرة المحلية")
    st.set_defaults(func=_cmd_status)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
