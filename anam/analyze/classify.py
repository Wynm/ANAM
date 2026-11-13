"""مصنف المجالات — يقرر: هذا جديد «ما مجاله؟» من نصوصه ووسومه ولغته.

يعمل محلياً بالكامل (كلمات مفتاحية مرجحة) — بدون أي API مدفوع.
يعيد أعلى مجالين تطابقاً مع درجة ثقة بين 0 و1.
"""
from __future__ import annotations

from ..models import Item

# المجالات: المعرّف ← (الاسم العربي، كلمات مفتاحية)
DOMAINS: dict[str, tuple[str, list[str]]] = {
    "ai": ("الذكاء الاصطناعي والنماذج", [
        "llm", "gpt", "ai", "artificial intelligence", "machine learning", "ml ",
        "deep learning", "agent", "agentic", "rag", "embedding", "transformer",
        "diffusion", "openai", "anthropic", "claude", "gemini", "deepseek", "llama",
        "qwen", "mcp", "prompt", "fine-tun", "finetun", "inference", "nlp",
        "computer vision", "neural", "langchain", "llamaindex", "hugging",
        "vector", "generative", "genai", "model context", "a2a", "multimodal",
    ]),
    "automation": ("الأتمتة وسير العمل", [
        "automation", "automate", "workflow", "n8n", "zapier", "rpa", "cron",
        "scheduler", "pipeline", "playwright", "puppeteer", "selenium", "scraper",
        "scraping", "headless", "webhook", "no-code", "low-code", "orchestrat",
        "task runner", "robot", "bot ",
    ]),
    "microsaas": ("فرص SaaS وMicro-SaaS", [
        "saas", "boilerplate", "starter", "template", "billing", "stripe",
        "subscription", "dashboard", "admin panel", "landing page", "micro-saas",
        "microsaas", "waitlist", "multi-tenant", "multi tenant", "invoicing",
        "crm", "cms", "e-commerce", "ecommerce", "storefront",
    ]),
    "data": ("تحليل البيانات وحوكمتها", [
        "analytics", "data analysis", "data science", "etl", "elt", "dbt",
        "pandas", "visualization", "chart", "bi ", "business intelligence",
        "warehouse", "dashboard", "bigquery", "spark", "airflow", "observab",
        "metron", "metrics", "insight", "report", "csv", "sql",
    ]),
    "trading": ("التداول والتقنية المالية", [
        "trading", "crypto", "bitcoin", "binance", "stock", "forex", "backtest",
        "quant", "fintech", "finance", "defi", "exchange", "portfolio",
        "market data", "algorithmic", "futures", "options", "ledger",
    ]),
    "security": ("الأمن السيبراني", [
        "security", "pentest", "vulnerability", "cve", "exploit", "scanner",
        "sast", "dast", "owasp", "auth", "oauth", "encryption", "privacy",
        "zero-trust", "siem", "malware",
    ]),
    "webdev": ("تطوير الويب والواجهات", [
        "react", "next.js", "nextjs", "vue", "svelte", "angular", "tailwind",
        "css", "ui ", "component", "frontend", "fullstack", "full-stack", "ssr",
        "astro", "remix", "solid", "vite", "webassembly", "graphql",
    ]),
    "devtool": ("أدوات المطور والإنتاجية", [
        "cli", "sdk", "developer tool", "devtool", "productivity", "vscode",
        "ide", "linter", "formatter", "debug", "testing", "test", "benchmark",
        "package manager", "dotfiles", "terminal", "shell", "utility", "toolkit",
    ]),
    "devops": ("البنية التحتية وDevOps", [
        "docker", "kubernetes", "k8s", "terraform", "ansible", "ci/cd", "cicd",
        "github actions", " observability", "monitoring", "prometheus", "grafana",
        "cloud", "aws", "gcp", "azure", "serverless", "edge", "proxy", "gateway",
    ]),
    "mobile": ("تطبيقات الجوال", [
        "flutter", "react native", "ios", "android", "kotlin", "swift", "mobile",
        "expo", "compose",
    ]),
    "life": ("الحياة الشخصية والتنظيم", [
        "todo", "note", "journal", "habit", "life", "personal", "health",
        "fitness", "recipe", "language learning", "education", "learning",
        "study", "knowledge", "second brain", "obsidian",
    ]),
    "content": ("صناعة المحتوى والتسويق", [
        "content", "blog", "seo", "marketing", "social media", "newsletter",
        "copywriting", "video", "podcast", "thumbnail", "youtube", "twitter",
        "linkedin", "email marketing", "growth",
    ]),
    "opensource": ("مشاريع مفتوحة المصدر عامة", [
        "open source", "open-source", "oss", "awesome", "library", "framework",
    ]),
}

_DEFAULT = ("عام / غير مصنف", [])


def classify(item: Item) -> list[tuple[str, str, float]]:
    """أعد قائمة (domain_id, الاسم العربي, درجة الثقة 0..1) مرتبة تنازلياً."""
    haystack = " ".join([
        item.name, item.description, item.language,
        " ".join(item.topics), str(item.raw.get("version", "")),
    ]).lower()

    scores: dict[str, float] = {}
    for domain, (_label, keywords) in DOMAINS.items():
        hits = 0.0
        for kw in keywords:
            if kw in haystack:
                # الكلمات الأطول دلالتها أقوى
                hits += min(len(kw), 14) / 7.0
        # مكافأة إذا طابق topic بدقة
        for topic in item.topics:
            if topic.lower() in DOMAINS.get(domain, ("", []))[1]:
                hits += 2.0
        if hits > 0:
            scores[domain] = hits

    if not scores:
        return [("opensource", DOMAINS["opensource"][0], 0.2)]

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[0][1]
    return [
        (d, DOMAINS[d][0], round(min(1.0, s / (top + 2.0)) , 2))
        for d, s in ranked[:3]
    ]


def primary_domain(item: Item) -> tuple[str, str]:
    results = classify(item)
    return results[0][0], results[0][1]
