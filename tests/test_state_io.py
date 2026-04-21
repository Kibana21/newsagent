import json
from datetime import date, timedelta
from src.utils.state_io import load_sent_urls, save_sent_urls, prune_sent_urls, recent_urls


def test_load_returns_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_sent_urls() == []


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = [{"url": "https://x/1", "sent_at": date.today().isoformat(),
                "title": "T", "buzz_score": 1, "insurance_score": 2}]
    save_sent_urls(entries)
    loaded = load_sent_urls()
    assert loaded[0]["url"] == "https://x/1"


def test_prune_removes_old_entries():
    today = date.today()
    entries = [
        {"url": "https://old/1", "sent_at": (today - timedelta(days=35)).isoformat()},
        {"url": "https://new/1", "sent_at": today.isoformat()},
    ]
    pruned = prune_sent_urls(entries, days=30)
    assert len(pruned) == 1
    assert pruned[0]["url"] == "https://new/1"


def test_recent_urls_filters_by_days(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    today = date.today()
    entries = [
        {"url": "https://recent/1", "sent_at": today.isoformat()},
        {"url": "https://old/1", "sent_at": (today - timedelta(days=10)).isoformat()},
    ]
    save_sent_urls(entries)
    recent = recent_urls(days=7)
    assert "https://recent/1" in recent
    assert "https://old/1" not in recent
