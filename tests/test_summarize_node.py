from src.nodes.summarize_node import summarize_node


def _state_with(business=None, technical=None, research=None, insurtech=None):
    return {
        "categorized_news": {
            "business": business or [],
            "technical": technical or [],
            "research": research or [],
            "insurtech": insurtech or [],
        },
        "buzz_scores": {},
        "curated_news": [],
        "tavily_news": [], "rss_news": [], "arxiv_news": [], "github_news": [],
        "hf_news": [], "hn_news": [], "reddit_news": [], "youtube_news": [],
    }


def test_empty_sections_produce_header_only(mock_llm):
    out = summarize_node(_state_with())
    assert "AIA GenAI Intelligence" in out["final_report"]


def test_business_section_rendered(mock_llm):
    item = {"title": "Big AI News", "url": "https://x/1", "summary": "Important.", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Business & Strategy" in out["final_report"]
    assert "Big AI News" in out["final_report"]


def test_boardroom_angle_injected(mock_llm):
    item = {"title": "Big AI News", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Boardroom angle" in out["final_report"]


def test_insurtech_competitor_flag(mock_llm):
    item = {"title": "Prudential launches AI", "url": "https://x/2", "summary": "s",
            "published_at": "", "competitor": True, "regulatory": False}
    out = summarize_node(_state_with(insurtech=[item]))
    assert "🏢" in out["final_report"]


def test_insurtech_regulatory_flag(mock_llm):
    item = {"title": "MAS guidance", "url": "https://x/3", "summary": "s",
            "published_at": "", "competitor": False, "regulatory": True}
    out = summarize_node(_state_with(insurtech=[item]))
    assert "⚖️" in out["final_report"]


def test_source_health_footer_present(mock_llm):
    out = summarize_node(_state_with())
    assert "Source Health" in out["final_report"]


def test_tldr_present_when_items_exist(mock_llm):
    item = {"title": "T", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "TL;DR" in out["final_report"]
