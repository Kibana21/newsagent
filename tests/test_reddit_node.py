import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.nodes.reddit_node import reddit_node

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_response():
    r = MagicMock()
    r.json.return_value = json.loads((FIXTURES / "reddit_top.json").read_text())
    r.raise_for_status = MagicMock()
    return r


def test_happy_path():
    with patch("src.nodes.reddit_node.requests.get", return_value=_mock_response()):
        out = reddit_node({})
    assert len(out["reddit_news"]) >= 1
    assert out["reddit_news"][0]["source"] == "reddit"


def test_partial_failure_still_returns_others():
    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("first sub failed")
        return _mock_response()

    with patch("src.nodes.reddit_node.requests.get", side_effect=_side_effect):
        out = reddit_node({})
    # Second subreddit should still return results
    assert len(out["reddit_news"]) >= 1
