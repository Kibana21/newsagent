from unittest.mock import MagicMock, patch
from src.nodes.rss_node import rss_node


def _fake_feed(entries):
    feed = MagicMock()
    feed.entries = entries
    return feed


def _entry(title="T", link="https://x/1", summary="s",
           published_parsed=(2026, 4, 21, 10, 0, 0, 0, 111, 0)):
    e = MagicMock()
    e.get = lambda k, default=None: {
        "title": title, "link": link, "summary": summary,
        "published_parsed": published_parsed,
    }.get(k, default)
    return e


def test_happy_path():
    with patch("src.nodes.rss_node.feedparser.parse", return_value=_fake_feed([_entry()])):
        out = rss_node({"days": 7})
    assert len(out["rss_news"]) >= 1
    assert out["rss_news"][0]["source"] == "rss"


def test_empty_feed():
    with patch("src.nodes.rss_node.feedparser.parse", return_value=_fake_feed([])):
        out = rss_node({"days": 2})
    assert out["rss_news"] == []


def test_old_entry_filtered_out():
    old = _entry(published_parsed=(2020, 1, 1, 0, 0, 0, 0, 1, 0))
    with patch("src.nodes.rss_node.feedparser.parse", return_value=_fake_feed([old])):
        out = rss_node({"days": 2})
    assert out["rss_news"] == []


def test_exception_returns_empty():
    with patch("src.nodes.rss_node.feedparser.parse", side_effect=Exception("boom")):
        out = rss_node({"days": 2})
    assert out["rss_news"] == []
