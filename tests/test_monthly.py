import json
from unittest.mock import MagicMock, patch
from src import monthly


def _fake_llm(content: str) -> MagicMock:
    fake = MagicMock()
    fake.invoke.return_value.content = content
    return fake


def _entries(n: int = 3) -> list[dict]:
    return [
        {"url": f"https://x/{i}", "title": f"Title {i}", "sent_at": "2026-04-20",
         "buzz_score": n - i + 1, "insurance_score": 3}
        for i in range(1, n + 1)
    ]


def test_top_items_ranks_by_buzz_times_insurance(monkeypatch):
    data = [
        {"url": "u1", "title": "T1", "sent_at": "2026-04-20", "buzz_score": 3, "insurance_score": 3},
        {"url": "u2", "title": "T2", "sent_at": "2026-04-19", "buzz_score": 5, "insurance_score": 1},
        {"url": "u3", "title": "T3", "sent_at": "2026-04-18", "buzz_score": 2, "insurance_score": 3},
    ]
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: data)
    top = monthly._top_items(limit=3)
    # Scores: u1=9, u3=6, u2=5
    assert [e["url"] for e in top] == ["u1", "u3", "u2"]


def test_top_items_deduplicates_by_url(monkeypatch):
    data = [
        {"url": "u1", "title": "T1", "sent_at": "2026-04-20", "buzz_score": 3, "insurance_score": 3},
        {"url": "u1", "title": "T1 again", "sent_at": "2026-04-19", "buzz_score": 2, "insurance_score": 3},
    ]
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: data)
    top = monthly._top_items(limit=10)
    assert len(top) == 1


def test_build_monthly_renders_with_llm_json(monkeypatch):
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: _entries(3))
    llm_response = json.dumps({
        "opening": "April was defined by agentic AI breakthroughs.",
        "rationales": [{"url": "https://x/1", "sentence": "Critical for underwriting teams."}],
    })
    monkeypatch.setattr("src.monthly.get_llm", lambda temperature=0.3: _fake_llm(llm_response))
    report = monthly.build_monthly_report()
    assert "Best of the Month" in report
    assert "April was defined by" in report
    assert "Critical for underwriting" in report


def test_build_monthly_graceful_on_bad_llm_json(monkeypatch):
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: _entries(3))
    monkeypatch.setattr("src.monthly.get_llm", lambda temperature=0.3: _fake_llm("not json {{"))
    report = monthly.build_monthly_report()
    # Should still render the ranked list even without LLM enrichment
    assert "Best of the Month" in report
    assert "Title 1" in report


def test_build_monthly_empty_history(monkeypatch):
    monkeypatch.setattr(monthly, "load_sent_urls", lambda: [])
    report = monthly.build_monthly_report()
    assert "No items" in report
