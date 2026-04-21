from src.utils.text import strip_html, title_similarity


def test_strip_html_removes_tags():
    assert strip_html("<b>hello</b> <em>world</em>") == "hello world"


def test_strip_html_empty_string():
    assert strip_html("") == ""


def test_strip_html_no_tags():
    assert strip_html("plain text") == "plain text"


def test_title_similarity_identical():
    assert title_similarity("OpenAI launches GPT-5", "OpenAI launches GPT-5") == 1.0


def test_title_similarity_near_duplicate():
    score = title_similarity("OpenAI launches GPT-5", "OpenAI launches GPT-5 model")
    assert score >= 0.85


def test_title_similarity_different():
    score = title_similarity("OpenAI launches GPT-5", "Anthropic releases Claude 4")
    assert score < 0.5


def test_title_similarity_empty():
    assert title_similarity("", "") == 1.0
    assert title_similarity("something", "") < 0.5
