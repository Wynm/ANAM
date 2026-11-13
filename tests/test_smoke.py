"""اختبارات دخانية — تعمل بدون شبكة."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anam.analyze.classify import classify, primary_domain
from anam.analyze.scoring import evaluate, _age_days
from anam.config import load_config
from anam.models import Item
from anam.storage import Store


def _item(**kw):
    base = dict(source="github", kind="repo", name="acme/cool-llm-agent",
                url="https://github.com/acme/cool-llm-agent",
                description="LLM agent with RAG for automation workflows",
                stars=250, created_at="2026-11-01T00:00:00Z",
                updated_at="2026-11-10T00:00:00Z",
                topics=["llm", "agent"], language="Python")
    base.update(kw)
    return Item(**base)


def test_classify_ai():
    item = _item()
    results = classify(item)
    assert results[0][0] == "ai"


def test_classify_trading():
    item = _item(name="acme/quant-backtest", description="crypto trading backtesting engine",
                 topics=["trading", "backtest"])
    did, _ = primary_domain(item)
    assert did == "trading"


def test_full_mode_keeps_everything(tmp_path):
    cfg = load_config(None)
    store = Store(tmp_path / "t.db")
    item = _item(stars=0, created_at="1999-01-01T00:00:00Z")
    store.upsert_item(item)
    ev = evaluate(item, store, cfg, "full")
    assert ev["keep"] is True
    store.close()


def test_normal_mode_filters_quiet_old_repo(tmp_path):
    cfg = load_config(None)
    store = Store(tmp_path / "t.db")
    item = _item(stars=5, created_at="2020-01-01T00:00:00Z", updated_at="2020-06-01T00:00:00Z")
    store.upsert_item(item)
    ev = evaluate(item, store, cfg, "normal")
    assert ev["keep"] is False
    store.close()


def test_normal_mode_keeps_hyped_new_repo(tmp_path):
    cfg = load_config(None)
    store = Store(tmp_path / "t.db")
    item = _item(stars=1500, created_at="2026-11-10T00:00:00Z")
    store.upsert_item(item)
    ev = evaluate(item, store, cfg, "normal")
    assert ev["keep"] is True
    store.close()


def test_age_days_parsing():
    assert _age_days("2026-11-01T00:00:00Z") > 0
    assert _age_days("") is None
