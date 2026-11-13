"""وحدة التشخيص — «شخّص أي جديد على الإنترنت» بدون أي شرط نجوم أو مشاهدات.

الاستخدام:
  anam diagnose owner/repo            # مستودع GitHub
  anam diagnose https://github.com/o/r
  anam diagnose @scope/pkg أو npm:pkg # حزمة npm
  anam diagnose "كلمة مفتاحية"         # بحث حر ثم تشخيص الأفضل

يعطي: ما هو؟ مجاله؟ صحته التقنية؟ كيف يثبّته ويستخدمه؟ أين ينفعك
(شغل/حياة/ربح/وقت)؟ وهل يستحق تبنّيه؟
"""
from __future__ import annotations

import base64
import datetime as _dt
import re
from pathlib import Path
from urllib.parse import quote, urlparse

from .analyze.classify import classify, primary_domain
from .analyze.scoring import _age_days
from .analyze.usecases import playbook_for
from .http import HttpError, get_json, github_token
from .models import Item


def _is_npmish(q: str) -> bool:
    return q.startswith("npm:") or q.startswith("@")


def _parse_github_url(q: str) -> str | None:
    m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", q)
    if m:
        return f"{m.group(1)}/{m.group(2).removesuffix('.git')}"
    return None


def diagnose(query: str, out_dir: str = "reports", cfg: dict | None = None) -> str:
    q = query.strip()
    gh_name = _parse_github_url(q)
    if gh_name:
        item, extra = _diagnose_repo(gh_name, cfg)
    elif _is_npmish(q):
        name = q.removeprefix("npm:").removeprefix("@")
        if q.startswith("@"):
            name = "@" + name
        item, extra = _diagnose_npm(name)
    elif re.fullmatch(r"[\w.\-]+/[\w.\-]+", q):
        item, extra = _diagnose_repo(q, cfg)
    else:
        item, extra = _diagnose_keyword(q, cfg)
    return _render(item, extra, out_dir)


# ---------------------------------------------------------------- GitHub
def _diagnose_repo(full_name: str, cfg: dict | None) -> tuple[Item, dict]:
    token = github_token((cfg or {}).get("github", {}).get("token_env", "GITHUB_TOKEN"))
    try:
        r = get_json(f"https://api.github.com/repos/{full_name}", token=token)
    except HttpError as e:
        raise SystemExit(f"تعذر جلب المستودع «{full_name}»: {e}")

    lic = r.get("license") or {}
    item = Item(
        source="github", kind="repo", name=r.get("full_name", full_name),
        url=r.get("html_url", f"https://github.com/{full_name}"),
        author=(r.get("owner") or {}).get("login", ""),
        description=r.get("description") or "",
        language=r.get("language") or "",
        stars=int(r.get("stargazers_count", 0)),
        forks=int(r.get("forks_count", 0)),
        issues=int(r.get("open_issues_count", 0)),
        license=lic.get("spdx_id") if isinstance(lic, dict) else None,
        created_at=r.get("created_at") or "",
        updated_at=r.get("pushed_at") or "",
        topics=list(r.get("topics") or []),
        raw={"archived": bool(r.get("archived")), "watchers": r.get("watchers_count", 0),
             "default_branch": r.get("default_branch", "main")},
    )

    readme_md, install_hint = _fetch_readme(full_name, token)
    extra = {"readme_excerpt": readme_md, "install_hint": install_hint}
    return item, extra


def _fetch_readme(full_name: str, token: str | None) -> tuple[str, str]:
    try:
        r = get_json(f"https://api.github.com/repos/{full_name}/readme", token=token)
        content = base64.b64decode(r.get("content", "")).decode("utf-8", errors="replace")
    except Exception:
        return "", ""
    excerpt = content[:1800]
    hint = ""
    m = re.search(r"(npm (?:install|i)|pip install|cargo add|go get|brew install|docker (?:run|pull)|pnpm add|yarn add)[^\n`]{0,120}", content)
    if m:
        hint = m.group(0).strip()
    return excerpt, hint


# ------------------------------------------------------------------ npm
def _diagnose_npm(name: str) -> tuple[Item, dict]:
    try:
        r = get_json(f"https://registry.npmjs.org/{quote(name, safe='@/')}")
    except HttpError as e:
        raise SystemExit(f"تعذر جلب الحزمة «{name}» من npm: {e}")

    latest = (r.get("dist-tags") or {}).get("latest", "")
    ver = (r.get("versions") or {}).get(latest, {}) if latest else {}
    time_info = r.get("time") or {}
    item = Item(
        source="npm", kind="package", name=name,
        url=f"https://www.npmjs.com/package/{name}",
        author=str(r.get("maintainers") or [{}])[:0] or _npm_author(r),
        description=r.get("description") or "",
        language="JavaScript/TypeScript",
        license=(ver.get("license") or r.get("license") or None),
        created_at=time_info.get("created", ""),
        updated_at=time_info.get("modified", ""),
        topics=list(r.get("keywords") or []),
        raw={"version": latest, "weekly_hint": "انظر npmjs.com للتحميلات"},
    )
    readme = (r.get("readme") or "")[:1800]
    hint = f"npm install {name}"
    return item, {"readme_excerpt": readme, "install_hint": hint}


def _npm_author(r: dict) -> str:
    m = r.get("maintainers") or []
    if m and isinstance(m, list) and isinstance(m[0], dict):
        return m[0].get("name", "")
    return str(r.get("author", ""))[:80]


# -------------------------------------------------------------- keyword
def _diagnose_keyword(q: str, cfg: dict | None) -> tuple[Item, dict]:
    token = github_token((cfg or {}).get("github", {}).get("token_env", "GITHUB_TOKEN"))
    url = f"https://api.github.com/search/repositories?q={quote(q)}&sort=stars&order=desc&per_page=1"
    try:
        data = get_json(url, token=token)
    except HttpError as e:
        raise SystemExit(f"تعذر البحث عن «{q}»: {e}")
    items = data.get("items", [])
    if not items:
        raise SystemExit(f"لم يُعثر على أي نتيجة لـ «{q}»")
    return _diagnose_repo(items[0]["full_name"], cfg)


# ------------------------------------------------------------- التشخيص
def _health(item: Item) -> list[str]:
    notes: list[str] = []
    age = _age_days(item.created_at)
    pushed = _age_days(item.updated_at)

    if item.raw.get("archived"):
        notes.append("⚠️ المستودع **مؤرشف** — لا يُنصح بتبنيه لمشاريع جديدة")
    if not item.license:
        notes.append("⚠️ بدون رخصة واضحة — الاستخدام التجاري محفوف بالمخاطر")
    else:
        notes.append(f"✅ رخصة: {item.license}")

    if pushed is not None:
        if pushed <= 30:
            notes.append(f"✅ نشط — آخر تحديث منذ {pushed:.0f} يوم")
        elif pushed <= 180:
            notes.append(f"🟡 تحديث متوسط — آخر نشاط منذ {pushed:.0f} يوم")
        else:
            notes.append(f"🔴 خامل — آخر نشاط منذ {pushed:.0f} يوم")

    if item.issues and item.stars:
        ratio = item.issues / max(item.stars, 1)
        if ratio > 0.3:
            notes.append(f"⚠️ نسبة المشاكل المفتوحة مرتفعة ({item.issues} مقابل {item.stars} نجمة)")
    if item.forks and item.stars:
        notes.append(f"نسبة الاستنساخ إلى النجوم: {item.forks / max(item.stars, 1):.2f} "
                     f"(أعلى = استخدام فعلي أكثر)")
    if age is not None:
        notes.append(f"عمر المشروع: {age:.0f} يوم")
    return notes


def _verdict(item: Item) -> str:
    pushed = _age_days(item.updated_at)
    score = 0
    score += 2 if item.stars >= 1000 else 1 if item.stars >= 100 else 0
    score += 2 if (pushed is not None and pushed <= 60) else 0
    score += 1 if item.license else 0
    score += 1 if not item.raw.get("archived") else -3
    if score >= 4:
        return "🟢 يستحق التجربة والتبنّي الجاد"
    if score >= 2:
        return "🟡 جرّب في مشروع صغير أولاً قبل الاعتماد عليه"
    return "🔴 لا تعتمد عليه الآن — ابحث عن بديل أنضج"


# -------------------------------------------------------------- العرض
def _render(item: Item, extra: dict, out_dir: str) -> str:
    domain_id, domain_label = primary_domain(item)
    play = playbook_for(domain_id)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", item.name.lower()).strip("-")[:60] or "item"
    date = _dt.date.today().isoformat()
    path = Path(out_dir) / f"diagnose-{slug}-{date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# 🩺 تشخيص: {item.name}",
        "",
        f"- **الرابط:** {item.url}",
        f"- **المصدر:** {item.source} | **النوع:** {item.kind} | **الرخصة:** {item.license or 'غير محددة'}",
        f"- **الواجهة/اللغة:** {item.language or 'غير محددة'}",
        (f"- **المؤشرات:** ⭐ {item.stars:,} نجمة | 🍴 {item.forks:,} فرع | 🐞 {item.issues} مشكلة مفتوحة"
         + (f" | ⬇️ {item.downloads_week:,} تحميل/أسبوع" if item.downloads_week else ""))
        if item.source != "npm" else
        f"- **المؤشرات:** ⬇️ تحميلات أسبوعية متوفرة على صفحة الحزمة | الإصدار: {item.raw.get('version', '?')}",
        f"- **التصنيفات المرجحة:** " + "، ".join(f"{label} ({s})" for _id, label, s in classify(item)),
        "",
        "## ما هو؟",
        item.description or "_لا يوجد وصف — راجع المستودع مباشرة._",
        "",
        "## مجاله الأساسي",
        f"**{domain_label}**",
        "",
        "## التشخيص الصحي",
        *[f"- {n}" for n in _health(item)],
        "",
        f"## الحكم: {_verdict(item)}",
        "",
        "## كيف تثبّته وتستخدمه؟",
        f"- تثبيت مقترح: `{extra.get('install_hint') or 'راجع قسم README الرسمي'}`",
        f"- استكشف التوثيق: {item.url}",
    ]
    excerpt = extra.get("readme_excerpt") or ""
    if excerpt:
        lines += ["", "### مقتطف من README", "```", excerpt.strip(), "```"]

    lines += ["", "## أين يفيدك؟ (تفصيل لكل مجال حياتي)"]
    labels = {"work": "💼 في الشغل والعمل", "profit": "💰 في الربح وبناء مصدر دخل",
              "life": "🌱 في الحياة الشخصية", "time": "⏱️ في اختصار الوقت والجهد",
              "saas": "🚀 كفرصة SaaS / Micro-SaaS"}
    for key, title in labels.items():
        lines += ["", f"### {title}"]
        lines += [f"- {u}" for u in play.get(key, [])]

    lines += ["", "---", f"_تشخيص وُلّد آلياً بواسطة ANAM — {date}. صحّح الحكم دائماً بمراجعتك الشخصية قبل الاعتماد._"]

    text = "\n".join(lines)
    path.write_text(text, encoding="utf-8")
    return text + f"\n\n📝 حُفظ التقرير في: {path}"
