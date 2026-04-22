from src.nodes.summarize_node import summarize_node


def _state_with(
    models=None, frameworks=None, security=None, research=None,
    enterprise=None, regulatory=None, business=None, insurtech=None, emerging=None,
):
    return {
        "categorized_news": {
            "models": models or [],
            "frameworks": frameworks or [],
            "security": security or [],
            "research": research or [],
            "enterprise": enterprise or [],
            "regulatory": regulatory or [],
            "business": business or [],
            "insurtech": insurtech or [],
            "emerging": emerging or [],
        },
        "buzz_scores": {},
        "curated_news": [],
        "tavily_news": [], "rss_news": [], "arxiv_news": [], "github_news": [],
        "hf_news": [], "hn_news": [], "reddit_news": [], "youtube_news": [], "serp_news": [],
    }


# ── Core output ───────────────────────────────────────────────────────────────

def test_empty_sections_produce_header_only(mock_llm):
    out = summarize_node(_state_with())
    assert "AIA GenAI Intelligence" in out["final_report"]


def test_reading_time_present(mock_llm):
    out = summarize_node(_state_with())
    assert "min read" in out["final_report"]


def test_source_health_shows_serp(mock_llm):
    out = summarize_node(_state_with())
    assert "SerpAPI" in out["final_report"]


# ── Editor's Take ─────────────────────────────────────────────────────────────

def test_editors_take_present(mock_llm):
    item = {"title": "Big News", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Editor's Take" in out["final_report"]


# ── Dual TL;DR ────────────────────────────────────────────────────────────────

def test_dual_tldr_executives_present(mock_llm):
    item = {"title": "T", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Executives" in out["final_report"]


def test_dual_tldr_engineers_present(mock_llm):
    item = {"title": "T", "url": "https://x/1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Engineers" in out["final_report"]


# ── Model Releases ────────────────────────────────────────────────────────────

def test_model_releases_section_rendered(mock_llm):
    item = {"title": "GPT-5 Released", "url": "https://x/m1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(models=[item]))
    assert "Model Releases" in out["final_report"]
    assert "GPT-5" in out["final_report"]


def test_model_release_card_shows_aia_use_case(mock_llm):
    item = {"title": "GPT-5 Released", "url": "https://x/m1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(models=[item]))
    assert "AIA use case" in out["final_report"]


# ── Security Threat Intel ─────────────────────────────────────────────────────

def test_security_section_rendered(mock_llm):
    item = {"title": "Prompt injection found", "url": "https://x/s1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(security=[item]))
    assert "Security Threat Intel" in out["final_report"]


def test_security_critical_badge(mock_llm):
    item = {"title": "Critical exploit", "url": "https://x/s1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(security=[item]))
    assert "🔴 CRITICAL" in out["final_report"]


def test_security_this_week_summary(mock_llm):
    items = [
        {"title": "Attack 1", "url": "https://x/s1", "summary": "s", "published_at": ""},
        {"title": "Attack 2", "url": "https://x/s2", "summary": "s", "published_at": ""},
    ]
    out = summarize_node(_state_with(security=items))
    assert "This week:" in out["final_report"]


# ── Framework Watch ───────────────────────────────────────────────────────────

def test_framework_watch_rendered(mock_llm):
    item = {"title": "New RAG framework", "url": "https://x/f1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(frameworks=[item]))
    assert "Framework Watch" in out["final_report"]


def test_framework_try_badge(mock_llm):
    item = {"title": "New RAG framework", "url": "https://x/f1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(frameworks=[item]))
    assert "✅ Try today" in out["final_report"]


# ── Enterprise Stories ────────────────────────────────────────────────────────

def test_enterprise_section_rendered(mock_llm):
    item = {"title": "Bank deploys AI", "url": "https://x/e1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(enterprise=[item]))
    assert "Enterprise Stories" in out["final_report"]


def test_enterprise_success_icon(mock_llm):
    item = {"title": "Bank deploys AI", "url": "https://x/e1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(enterprise=[item]))
    assert "✅" in out["final_report"]


# ── Regulatory Radar ──────────────────────────────────────────────────────────

def test_regulatory_section_rendered(mock_llm):
    item = {"title": "MAS AI guidance", "url": "https://x/r1", "summary": "s",
            "published_at": "", "regulatory": True}
    out = summarize_node(_state_with(regulatory=[item]))
    assert "Regulatory Radar" in out["final_report"]


def test_regulatory_deadline_badge(mock_llm):
    item = {"title": "MAS AI guidance", "url": "https://x/r1", "summary": "s",
            "published_at": "", "regulatory": True}
    out = summarize_node(_state_with(regulatory=[item]))
    assert "DEADLINE" in out["final_report"]


# ── Emerging Concepts ─────────────────────────────────────────────────────────

def test_emerging_concepts_rendered(mock_llm):
    item = {"title": "Compound AI systems", "url": "https://x/c1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(emerging=[item]))
    assert "Emerging Concepts" in out["final_report"]


def test_emerging_dual_audience_labels(mock_llm):
    item = {"title": "Compound AI systems", "url": "https://x/c1", "summary": "s", "published_at": ""}
    out = summarize_node(_state_with(emerging=[item]))
    assert "For engineers" in out["final_report"]
    assert "For leadership" in out["final_report"]


# ── Existing sections still work ──────────────────────────────────────────────

def test_business_section_rendered(mock_llm):
    item = {"title": "Big AI News", "url": "https://x/b1", "summary": "Important.", "published_at": ""}
    out = summarize_node(_state_with(business=[item]))
    assert "Business & Strategy" in out["final_report"]
    assert "Boardroom angle" in out["final_report"]


def test_insurtech_competitor_flag(mock_llm):
    item = {"title": "Prudential launches AI", "url": "https://x/i1", "summary": "s",
            "published_at": "", "competitor": True, "regulatory": False}
    out = summarize_node(_state_with(insurtech=[item]))
    assert "🏢" in out["final_report"]


def test_action_badge_act_rendered(mock_llm):
    item = {"title": "Urgent AI", "url": "https://x/b1", "summary": "s",
            "published_at": "", "action_signal": "act"}
    out = summarize_node(_state_with(business=[item]))
    assert "🔴 Act" in out["final_report"]


def test_feedback_footer_present(mock_llm, monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "test@example.com")
    out = summarize_node(_state_with())
    assert "Was today's edition useful" in out["final_report"]


def test_last_edition_hook_shown(mock_llm, monkeypatch):
    monkeypatch.setattr("src.nodes.summarize_node.load_last_edition", lambda: {
        "date": "2026-04-20", "top_url": "https://x/prev", "top_headline": "Previous top story",
    })
    out = summarize_node(_state_with())
    assert "Last" in out["final_report"]
