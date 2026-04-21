import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.nodes.github_node import github_node

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_response(data: dict):
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status = MagicMock()
    return r


def test_happy_path(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    data = json.loads((FIXTURES / "github_repos.json").read_text())
    with patch("src.nodes.github_node.requests.get", return_value=_mock_response(data)):
        out = github_node({"days": 2})
    assert len(out["github_news"]) >= 1
    assert out["github_news"][0]["source"] == "github"


def test_with_token_adds_auth_header(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "mytoken")
    data = json.loads((FIXTURES / "github_repos.json").read_text())
    with patch("src.nodes.github_node.requests.get", return_value=_mock_response(data)) as mock_get:
        github_node({"days": 2})
    call_kwargs = mock_get.call_args_list[0][1]
    assert "Authorization" in call_kwargs.get("headers", {})


def test_exception_returns_empty():
    with patch("src.nodes.github_node.requests.get", side_effect=Exception("403")):
        out = github_node({"days": 2})
    assert out["github_news"] == []
