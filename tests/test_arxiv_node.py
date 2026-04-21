from pathlib import Path
from unittest.mock import MagicMock, patch
from src.nodes.arxiv_node import arxiv_node

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_response(text: str):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_happy_path():
    xml = (FIXTURES / "arxiv_atom.xml").read_text()
    with patch("src.nodes.arxiv_node.requests.get", return_value=_mock_response(xml)):
        out = arxiv_node({"days": 2})
    assert len(out["arxiv_news"]) >= 1
    assert out["arxiv_news"][0]["source"] == "arxiv"


def test_lag_buffer_includes_older_papers():
    xml = (FIXTURES / "arxiv_atom.xml").read_text()
    with patch("src.nodes.arxiv_node.requests.get", return_value=_mock_response(xml)):
        out = arxiv_node({"days": 1})
    # lag buffer = days+2, so 3 days back — both fixture entries are within range
    assert len(out["arxiv_news"]) >= 1


def test_exception_returns_empty():
    with patch("src.nodes.arxiv_node.requests.get", side_effect=Exception("timeout")):
        out = arxiv_node({"days": 2})
    assert out["arxiv_news"] == []
