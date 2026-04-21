import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.nodes.hf_node import hf_node

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_response(data):
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status = MagicMock()
    return r


def test_happy_path():
    data = json.loads((FIXTURES / "hf_models.json").read_text())
    with patch("src.nodes.hf_node.requests.get", return_value=_mock_response(data)):
        out = hf_node({})
    assert len(out["hf_news"]) >= 1
    assert out["hf_news"][0]["source"] == "huggingface"
    assert "huggingface.co" in out["hf_news"][0]["url"]


def test_exception_returns_empty():
    with patch("src.nodes.hf_node.requests.get", side_effect=Exception("timeout")):
        out = hf_node({})
    assert out["hf_news"] == []
