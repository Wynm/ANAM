"""محرك الضجة والفلترة — قلب الوضعين (العادي / التام).

الوضع العادي (الافتراضي): لا يمرّر إلا ما يُحدث ضجة — صعود ملفت في
النجوم/التحميلات، أو عتبة مطلقة للمشاريع حديثة الولادة.
الوضع التام: يمرّر كل ما جُمع بلا فلترة (مع سقف اختياري لحجم التقرير).
وضع التشخيص: لا توجد عتبات أصلاً — انظر anam/diagnose.py.
"""
from __future__ import annotations

import datetime as _dt
import time
from typing import Optional

from ..models import Item
from ..storage import Store

_DAY = 86400.0


def _age_days(created_at: str) -> Optional[float]:
    if not created_at:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            dt = _dt.datetime.strptime(created_at.strip(), fmt)
            now = _dt.datetime.now(dt.tzinfo) if dt.tzinfo else _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
            return max((now - dt).total_seconds() / _DAY, 0.0)
        except ValueError:
            try:
                dt = _dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = _dt.datetime.now(dt.tzinfo) if dt.tzinfo else _dt.datetime.now(_dt.timezone.utc)
                return max((now - dt).total_seconds() / _DAY, 0.0)
            except ValueError:
                continue
    return None


def star_velocity(item: Item, store: Store) -> Optional[float]:
    """نجوم/اليوم: بين آخر لقطتين، وإلا منذ الإنشاء."""
    try:
        latest, prev = store.velocity_pair(item.uid)
    except Exception:
        latest, prev = None, None
    if latest is not None and prev is not None:
        dt_days = (float(latest["ts"]) - float(prev["ts"])) / _DAY
        if dt_days >= (0.5 / 24):  # على الأقل ~30 دقيقة بين اللقطتين
            return (int(latest["stars"]) - int(prev["stars"])) / dt_days
    age = _age_days(item.created_at)
    if age is not None and age > 0:
        return item.stars / age
    return None


def download_velocity(item: Item, store: Store) -> Optional[float]:
    if item.downloads_week is None:
        return None
    try:
        latest, prev = store.velocity_pair(item.uid)
    except Exception:
        latest, prev = None, None
    if (latest is not None and prev is not None
            and latest["downloads_week"] is not None and prev["downloads_week"] is not None):
        dt_days = (float(latest["ts"]) - float(prev["ts"])) / _DAY
        if dt_days >= (0.5 / 24):
            return (int(latest["downloads_week"]) - int(prev["downloads_week"])) / dt_days
    return None


def hype_score(item: Item, store: Store) -> float:
    """درجة ضجة 0..100 للترتيب داخل التقرير."""
    vel = star_velocity(item, store) or 0.0
    age = _age_days(item.created_at)
    freshness = max(0.0, 1.0 - (age / 60.0)) if age is not None else 0.3
    stars_pts = min(item.stars / 2000.0, 1.0) * 35
    vel_pts = min(vel / 150.0, 1.0) * 40
    dl_pts = min((item.downloads_week or 0) / 200000.0, 1.0) * 15
    fresh_pts = freshness * 10
    return round(stars_pts + vel_pts + dl_pts + fresh_pts, 1)


def evaluate(item: Item, store: Store, cfg: dict, mode: str) -> dict:
    """قرر: هل يدخل التقرير؟ ولماذا؟ يعمل للوضعين."""
    f = cfg.get("filters", {})
    age = _age_days(item.created_at)
    vel = star_velocity(item, store)
    dl_vel = download_velocity(item, store)
    score = hype_score(item, store)

    signals = {
        "age_days": round(age, 1) if age is not None else None,
        "star_velocity_per_day": round(vel, 2) if vel is not None else None,
        "download_velocity_per_day": round(dl_vel, 1) if dl_vel is not None else None,
        "hype_score": score,
    }

    if mode == "full":
        return {"keep": True, "reason": "الوضع التام: بلا فلترة", **signals}

    # ---- الوضع العادي: الضجة فقط ----
    reasons: list[str] = []
    recent = age is not None and age <= float(f.get("normal_recent_days", 45))

    if item.source == "rss":
        # موجزات RSS الافتراضية (HN مثلاً) هي بحد ذاتها قائمة الضجة اليومية
        return {"keep": True, "reason": "خبر ضمن موجز ضجة منتقى تحريرياً", **signals}

    if item.source == "npm":
        dl = item.downloads_week or 0
        if dl >= int(f.get("npm_min_weekly_downloads", 50000)):
            reasons.append(f"تحميلات أسبوعية {dl:,} ≥ الحد")
        if dl_vel is not None and dl_vel >= 200:
            reasons.append(f"تسارع تحميلات +{dl_vel:,.0f}/يوم")
        if item.raw.get("dependents") and str(item.raw["dependents"]).isdigit() \
                and int(item.raw["dependents"]) >= 50:
            reasons.append(f"{item.raw['dependents']} حزمة تعتمد عليه")
    else:  # github
        if item.stars >= int(f.get("normal_min_stars", 500)) and recent:
            reasons.append(f"{item.stars:,} نجمة ومولود منذ {age:.0f} يوم")
        if vel is not None and vel >= float(f.get("normal_min_star_velocity_per_day", 25.0)):
            reasons.append(f"سرعة صعود {vel:.1f} نجمة/يوم")

    return {
        "keep": bool(reasons),
        "reason": "؛ ".join(reasons) if reasons else "لا توجد ضجة ملفتة — تجاوز في الوضع العادي",
        **signals,
    }
