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


def test_reading_time_present(mock_llm):
    out = summarize_node(_state_with())
    assert "min read" in out["final_report"]


def test_editors_take_present(mock_llm):
    item = {"title": "Big News", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Editor's Take" in out["final_report"]


def test_action_badge_act_rendered(mock_llm):
    item = {"title": "Urgent AI", "url": "https://x/1", "summary": "s",
            "published_at": "", "action_signal": "act"}
    out = summarize_node(_state_with(business=[item]))
    assert "🔴 Act" in out["final_report"]


def test_action_badge_watch_rendered(mock_llm):
    item = {"title": "Developing Story", "url": "https://x/1", "summary": "s",
            "published_at": "", "action_signal": "watch"}
    out = summarize_node(_state_with(business=[item]))
    assert "🟡 Watch" in out["final_report"]


def test_sentiment_badge_opportunity_rendered(mock_llm):
    item = {"title": "New Tool", "url": "https://x/1", "summary": "s",
            "published_at": "", "sentiment": "opportunity"}
    out = summarize_node(_state_with(insurtech=[item]))
    assert "📈" in out["final_report"]


def test_sentiment_badge_risk_rendered(mock_llm):
    item = {"title": "Competitor Move", "url": "https://x/1", "summary": "s",
            "published_at": "", "sentiment": "risk"}
    out = summarize_node(_state_with(insurtech=[item]))
    assert "⚠️" in out["final_report"]


def test_heatmap_section_present(mock_llm):
    item = {"title": "OpenAI news", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "AI Lab Pulse" in out["final_report"]


def test_steal_this_week_present(mock_llm):
    item = {"title": "New Tool", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Steal This Week" in out["final_report"]


def test_feedback_footer_present(mock_llm, monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "test@example.com")
    item = {"title": "T", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Was today's edition useful" in out["final_report"]


def test_last_edition_hook_shown(mock_llm, tmp_path, monkeypatch):
    import json as _json
    from src.utils.edition_state import LAST_EDITION_PATH
    monkeypatch.setattr("src.utils.edition_state.LAST_EDITION_PATH", tmp_path / "last_edition.json")
    (tmp_path / "last_edition.json").write_text(_json.dumps({
        "date": "2026-04-20",
        "top_url": "https://x/prev",
        "top_headline": "Previous top story",
    }))
    monkeypatch.setattr("src.nodes.summarize_node.load_last_edition", lambda: {
        "date": "2026-04-20", "top_url": "https://x/prev", "top_headline": "Previous top story",
    })
    out = summarize_node(_state_with())
    assert "Last" in out["final_report"]
