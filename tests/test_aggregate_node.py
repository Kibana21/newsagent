from unittest.mock import patch
from src.nodes.aggregate_node import aggregate_node


def test_dedup_by_url():
    state = {
        "tavily_news": [{"title": "A", "url": "https://x/1", "source": "tavily"}],
        "rss_news":    [{"title": "A dup", "url": "https://x/1/", "source": "rss"}],
    }
    with patch("src.nodes.aggregate_node.recent_urls", return_value=set()):
        out = aggregate_node(state)
    assert len(out["raw_news"]) == 1


def test_sent_urls_filter_removes_recent():
    state = {"tavily_news": [{"title": "A", "url": "https://x/1", "source": "tavily"}]}
    with patch("src.nodes.aggregate_node.recent_urls", return_value={"https://x/1"}):
        out = aggregate_node(state)
    assert out["raw_news"] == []


def test_buzz_scoring_near_duplicates():
    state = {
        "tavily_news": [{"title": "OpenAI announces GPT-5 model release", "url": "https://a/1", "source": "tavily"}],
        "rss_news":    [{"title": "OpenAI announces GPT-5 model release today", "url": "https://b/2", "source": "rss"}],
        "hn_news":     [{"title": "OpenAI announces GPT-5 model release now", "url": "https://c/3", "source": "hn"}],
    }
    with patch("src.nodes.aggregate_node.recent_urls", return_value=set()):
        out = aggregate_node(state)
    assert max(out["buzz_scores"].values()) >= 2


def test_empty_sources_return_empty():
    state = {}
    with patch("src.nodes.aggregate_node.recent_urls", return_value=set()):
        out = aggregate_node(state)
    assert out["raw_news"] == []
    assert out["buzz_scores"] == {}
