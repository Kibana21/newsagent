from unittest.mock import MagicMock, patch
import pytest
from src.nodes.tavily_node import tavily_node


def _make_tool(results):
    tool = MagicMock()
    tool.invoke.return_value = {"results": results}
    return tool


def test_happy_path(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "fake")
    result = {"title": "T", "url": "https://x/1", "content": "summary", "published_date": "2026-04-20"}
    with patch("src.nodes.tavily_node.TavilySearch", return_value=_make_tool([result])):
        out = tavily_node({"search_query": "GenAI", "days": 2})
    assert len(out["tavily_news"]) >= 1
    assert out["tavily_news"][0]["source"] == "tavily"


def test_empty_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "fake")
    with patch("src.nodes.tavily_node.TavilySearch", return_value=_make_tool([])):
        out = tavily_node({"search_query": "GenAI", "days": 2})
    assert out["tavily_news"] == []


def test_exception_returns_empty(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "fake")
    with patch("src.nodes.tavily_node.TavilySearch", side_effect=Exception("boom")):
        out = tavily_node({"search_query": "GenAI", "days": 2})
    assert out["tavily_news"] == []


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        tavily_node({"search_query": "GenAI", "days": 2})
