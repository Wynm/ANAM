"""ANAM يستغل المستجدات لنفسه.

يفحص ما التقطه المسح مؤخراً ويقترح تحسينات ملموسة على ANAM نفسه:
تكاملات جديدة، مصادر إضافية، نماذج أذكى — مع الإشارة للعنصر الملهم.
لا يعدّل الكود تلقائياً؛ ينتج تقرير خطة عمل يمكن تنفيذه خطوة خطوة.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from .analyze.classify import primary_domain
from .models import Item

# (الاسم العربي للقدرة، كلمات مفتاحية في العناصر الملتقطة، الاقتراح)
IMPROVEMENT_MAP: list[tuple[str, list[str], str]] = [
    ("تلخيص التقارير بالذكاء الاصطناعي",
     ["llm", "gpt", "agent", "rag", "embedding", "summary", "summariz"],
     "دمج نموذج محلي أو API مجاني التوليد لتلخيص كل تقرير أسبوعياً في 5 نقاط تنفيذية."),
    ("كشف التكرار الدلالي بين العناصر",
     ["embedding", "vector", "dedup", "similarity", "semantic"],
     "استخدام embeddings لتجميع المشاريع المتشابهة (مثل 5 أطر RAG متشابهة) في بطاقة واحدة."),
    ("مصادر جديدة للالتقاط",
     ["rss", "feed", "hacker news", "product hunt", "trending", "changelog"],
     "إضافة موجزات Product Hunt وChangelogs الرسمية كمصدر Adapter جديد (rss.feeds)."),
    ("جدولة ونشر تلقائي للتقارير",
     ["github actions", "cron", "scheduler", "workflow", "ci/cd"],
     "الاستفادة من GitHub Actions/ cron لتشغيل ANAM دورياً ونشر التقارير كـReleases أو Pages."),
    ("لوحة ويب تفاعلية",
     ["dashboard", "chart", "visualization", "next.js", "svelte", "astro"],
     "بناء لوحة عرض ثابتة (GitHub Pages) تتغذى من reports/*.json — بدون خادم إطلاقاً."),
    ("كشف الفرص التجارية تلقائياً",
     ["saas", "micro-saas", "boilerplate", "starter", "template"],
     "توسيع قسم «الفرص المرشحة» بمقارنة الضجة بالمنافسة (عدد المستودعات المشابهة)."),
    ("إشعارات فورية عند ضجة كبيرة",
     ["webhook", "telegram", "slack", "notification", "bot"],
     "إرسال تنبيه (Telegram/Slack/Discord webhook مجاني) فور تجاوز عنصر عتبة الضجة."),
    ("تقييم جودة الكود الملتقط",
     ["sast", "linter", "code quality", "security scan", "benchmark"],
     "فحص اختياري للمستودعات المرشحة (lichess registry/OSV للمخاطر الأمنية في التبعيات)."),
]


def suggest(items: list[Item], out_dir: str = "reports") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = _dt.date.today().isoformat()
    path = out / f"self-improvement-{stamp}.md"

    matched: dict[str, dict] = {}  # capability -> {suggestion, examples: []}
    for item in items:
        hay = " ".join([item.name, item.description, " ".join(item.topics)]).lower()
        for capability, keywords, suggestion in IMPROVEMENT_MAP:
            if any(re.search(re.escape(k), hay) for k in keywords):
                bucket = matched.setdefault(capability, {"suggestion": suggestion, "examples": []})
                if len(bucket["examples"]) < 3 and all(e.uid != item.uid for e in bucket["examples"]):
                    bucket["examples"].append(item)

    lines = [
        "# 🔧 خطة تحسين ANAM الذاتي",
        "",
        f"- **التاريخ:** {stamp}",
        f"- **عناصر الفحص:** {len(items)}",
        f"- **قدرات مقترحة:** {len(matched)}",
        "",
        "ANAM يراجع ما التقطه مؤخراً ليطور نفسه: كل اقتراح أدناه مرتبط بعناصر حقيقية رُصدت.",
        "",
    ]
    if not matched:
        lines += ["لا توجد عناصر ملهمة بما يكفي هذه الدورة — كرر المسح بعد أيام.", ""]
    else:
        # رتّب حسب عدد الأمثلة الملهمة (الأكثر حضوراً أولاً)
        for capability, bucket in sorted(matched.items(),
                                         key=lambda kv: len(kv[1]["examples"]), reverse=True):
            lines += [f"## {capability} ({len(bucket['examples'])}+ عنصر مُلهم)",
                      f"- **الاقتراح:** {bucket['suggestion']}"]
            for item in bucket["examples"]:
                lines += [f"  - [{item.name}]({item.url}) — {(item.description or '')[:110]}"]
            lines += [""]

    lines += [
        "## ملاحظات قوة حالية في ANAM",
        "- **صفر تبعيات خارجية**: يعمل بمكتبة بايثون القياسية فقط — مجاني بالكامل ويعمل أي بيئة.",
        "- **مصادر مجانية 100%**: GitHub Search API + npm Registry + RSS — لا مفاتيح مدفوعة.",
        "- **ذاكرة SQLite محلية**: لا يحتاج خادم قاعدة بيانات.",
        "",
        "_نفّذ الاقتراحات حسب الأولوية: أيها أعلى أثراً على جودة التقرير بأقل جهد._",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
