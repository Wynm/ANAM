"""مولّد التقارير — يحوّل نتائج المسح إلى تقرير عربي عملي (Markdown + JSON).

كل عنصر في التقرير يجيب عن خمسة أسئلة:
1) ما هو؟  2) ما مجاله؟  3) كيف تستخدمه؟  4) كيف تستفيد منه (شغل/ربح/حياة/وقت/SaaS)؟  5) هل يستحق؟
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .analyze.classify import classify, primary_domain
from .analyze.usecases import playbook_for
from .models import Item


def build_report(evaluated: list[tuple[Item, dict]], mode: str, out_dir: str = "reports") -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    md_path = out / f"anam-report-{stamp}.md"
    json_path = out / f"anam-report-{stamp}.json"

    evaluated = sorted(evaluated, key=lambda pair: pair[1].get("hype_score", 0), reverse=True)

    domains: dict[str, list[tuple[Item, dict]]] = {}
    for item, ev in evaluated:
        did, _ = primary_domain(item)
        domains.setdefault(did, []).append((item, ev))

    md: list[str] = [
        f"# 📡 تقرير ANAM — رادار المستجدات",
        "",
        f"- **التاريخ:** {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- **الوضع:** {'العادي (الضجة فقط)' if mode == 'normal' else 'التام (كل المستجدات بدون فلترة)'}",
        f"- **عدد العناصر:** {len(evaluated)}",
        "",
        "## الخلاصة التنفيذية",
        _executive_summary(evaluated, domains),
        "",
        "## جدول المحتويات حسب المجال",
    ]
    for did, group in sorted(domains.items(), key=lambda kv: len(kv[1]), reverse=True):
        label = group[0] and classify(group[0][0])[0][1]
        md.append(f"- **{label}** — {len(group)} عنصر")

    md += ["", "---", ""]

    for did, group in sorted(domains.items(), key=lambda kv: len(kv[1]), reverse=True):
        label = classify(group[0][0])[0][1]
        md += [f"# 🗂️ مجال: {label}", ""]
        for i, (item, ev) in enumerate(group, 1):
            md += _item_section(i, item, ev, did)
        md += ["---", ""]

    md += [
        "## 💡 فرص مرشحة للتنفيذ الآن",
        _opportunities(evaluated),
        "",
        "## 🧭 كيف تقرأ هذا التقرير؟",
        "- رتّبنا العناصر بدرجة «الضجة» (نجوم/اليوم + حداثة + حجم التبني). ابدأ من الأعلى.",
        "- قبل تبني أي مشروع: اقرأ README، جربه على بيانات صغيرة، تحقق من الرخصة وتاريخ آخر تحديث.",
        "- لأي عنصر يعجبك، شخّصه بعمق: `anam diagnose <owner/repo | npm:pkg | الرابط>`",
        "",
        "_وُلّد آلياً بواسطة ANAM. الأرقام من GitHub وnpm وRSS وقت التوليد._",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")

    payload = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "count": len(evaluated),
        "items": [
            {**item.to_dict(), "evaluation": ev,
             "domains": [{"id": d, "label": l, "confidence": s} for d, l, s in classify(item)]}
            for item, ev in evaluated
        ],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path


def _executive_summary(evaluated: list[tuple[Item, dict]], domains: dict) -> str:
    if not evaluated:
        return "لم يلتقط هذا المسح أي مستجد يستوفي الشروط."
    top_domain = max(domains.items(), key=lambda kv: len(kv[1]))
    top_item = evaluated[0][0]
    return (
        f"التقط هذا المسح **{len(evaluated)}** مستجداً. المجال الأعلى نشاطاً: "
        f"**{classify(top_domain[1][0][0])[0][1]}** ({len(top_domain[1])} عنصر). "
        f"العنصر الأعلى ضجة حالياً: **{top_item.name}** "
        f"({top_item.stars:,} ⭐ على {top_item.source})."
    )


def _item_section(i: int, item: Item, ev: dict, domain_id: str) -> list[str]:
    play = playbook_for(domain_id)
    vel = ev.get("star_velocity_per_day")
    dl = item.downloads_week
    metrics = [f"⭐ {item.stars:,}", f"🍴 {item.forks:,}"]
    if vel is not None:
        metrics.append(f"🚀 {vel:.1f} نجمة/يوم")
    if dl is not None:
        metrics.append(f"⬇️ {dl:,}/أسبوع")
    metrics.append(f"🔥 ضجة {ev.get('hype_score', 0)}/100")

    how = _how_to_use(item)
    lines = [
        f"## {i}. {item.name}",
        f"**{item.url}**",
        "",
        f"- **ما هو؟** {item.description or 'راجع الرابط مباشرة — لا يوجد وصف.'}",
        f"- **المؤشرات:** {' | '.join(metrics)}",
        f"- **لماذا ظهر؟** {ev.get('reason', '—')}",
        f"- **التصنيف:** " + "، ".join(f"{l}" for _d, l, _s in classify(item)),
        f"- **الرخصة/اللغة:** {item.license or 'غير محددة'} / {item.language or 'غير محددة'}",
        "",
        "**كيف تستخدمه؟**",
        f"- {how}",
        f"- جربه معزولاً أولاً (فرع/حاوية/بيئة تجريبية)، اقرأ README، ثم قرر التبني.",
        "",
        "**أين يفيدك؟**",
        f"- 💼 **الشغل:** {play['work'][0]}",
        f"- 💰 **الربح:** {play['profit'][0]}",
        f"- 🌱 **الحياة:** {play['life'][0]}",
        f"- ⏱️ **الوقت:** {play['time'][0]}",
        f"- 🚀 **SaaS/Micro-SaaS:** {play['saas'][0]}",
        "",
    ]
    return lines


def _how_to_use(item: Item) -> str:
    if item.source == "npm":
        return f"ثبّته: `npm install {item.name}` ثم اقرأ أمثلة README واستخدمه كاعتمادية في مشروعك."
    if item.source == "github":
        if item.language and item.language.lower() in ("python",):
            return "استنسخه واتبع README (غالباً `pip install -r requirements.txt` ثم تشغيل المثال)، أو استورده كوحدة في مشروعك."
        if item.language and item.language.lower() in ("typescript", "javascript"):
            return "ثبّته عبر npm/pnpm/yarn حسب README، أو استنسخه وبنِه محلياً (`npm install && npm run build`)."
        if item.language and item.language.lower() in ("go",):
            return "استورده: `go get <الموديل>` أو ابنِه من المصدر واقرأ أمثلة `cmd/` أو `examples/`."
        if item.language and item.language.lower() in ("rust",):
            return "أضفه في `Cargo.toml` أو ابنِه من المصدر واقرأ مجلد `examples/`."
        return "اقرأ README أولاً، ثم اتبع قسم البدء السريع (Quickstart/Installation) — معظم المشاريع الجيدة توثقه بوضوح."
    return "اقرأ المادة الأصلية عبر الرابط، واستخرج منها الأداة/الفكرة ثم جرّبها في سياقك."


def _opportunities(evaluated: list[tuple[Item, dict]]) -> str:
    """رشّح عناصر ذات صلة بـMicro-SaaS/الأتمتة كفرص تنفيذ، بلا اختلاق بيانات."""
    candidates: list[str] = []
    for item, ev in evaluated:
        did, _ = primary_domain(item)
        if did in ("microsaas", "automation", "ai", "data", "content") and ev.get("hype_score", 0) >= 15:
            candidates.append(f"- **{item.name}** — يبني «{did}» جاهزاً؛ فكر بصيغة: نسخة مدفوعة مُدارة/مستضافة له بثمن اشتراك صغير. {item.url}")
        if len(candidates) >= 6:
            break
    if not candidates:
        return "لا توجد عناصر كافية الصلة ببناء منتجات في هذا المسح — سيتضح ذلك أكثر مع تراكم التشغيلات."
    return "\n".join(candidates)
