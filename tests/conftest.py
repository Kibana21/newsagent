from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture
def sample_state():
    return {
        "search_query": "latest GenAI",
        "days": 2,
        "tavily_news": [], "rss_news": [], "arxiv_news": [], "github_news": [],
        "hf_news": [], "hn_news": [], "reddit_news": [], "youtube_news": [], "serp_news": [],
    }


@pytest.fixture
def sample_news_item():
    return {
        "title": "OpenAI Announces GPT-5",
        "url": "https://openai.com/blog/gpt-5",
        "summary": "Big release.",
        "source": "rss",
        "published_at": "2026-04-20T10:00:00+00:00",
    }


@pytest.fixture
def mock_llm(monkeypatch):
    curate_response = json.dumps({
        "models": [{"title": "GPT-5 Released", "url": "https://x/m1", "summary": "Big model.",
                    "source": "serp", "published_at": "", "insurance_score": 2,
                    "competitor": False, "regulatory": False, "action_signal": "watch",
                    "sentiment": "opportunity", "quality_score": 3}],
        "frameworks": [{"title": "New RAG framework", "url": "https://x/f1", "summary": "Fast.",
                        "source": "serp", "published_at": "", "insurance_score": 1,
                        "competitor": False, "regulatory": False, "action_signal": "watch",
                        "sentiment": "neutral", "quality_score": 2}],
        "security": [{"title": "Prompt injection found", "url": "https://x/s1", "summary": "Risky.",
                      "source": "serp", "published_at": "", "insurance_score": 2,
                      "competitor": False, "regulatory": False, "action_signal": "act",
                      "sentiment": "risk", "quality_score": 3}],
        "research": [],
        "enterprise": [{"title": "Bank deploys AI", "url": "https://x/e1", "summary": "Works.",
                        "source": "serp", "published_at": "", "insurance_score": 2,
                        "competitor": False, "regulatory": False, "action_signal": "watch",
                        "sentiment": "opportunity", "quality_score": 2}],
        "regulatory": [{"title": "MAS AI guidance", "url": "https://x/r1", "summary": "New rules.",
                        "source": "rss", "published_at": "", "insurance_score": 3,
                        "competitor": False, "regulatory": True, "action_signal": "act",
                        "sentiment": "risk", "quality_score": 3}],
        "business": [{"title": "AIA AI News", "url": "https://x/b1", "summary": "Strategy.",
                      "source": "tavily", "published_at": "", "insurance_score": 3,
                      "competitor": False, "regulatory": False, "action_signal": "watch",
                      "sentiment": "opportunity", "quality_score": 2}],
        "insurtech": [],
        "emerging": [{"title": "Compound AI systems", "url": "https://x/c1", "summary": "New idea.",
                      "source": "serp", "published_at": "", "insurance_score": 1,
                      "competitor": False, "regulatory": False, "action_signal": "aware",
                      "sentiment": "neutral", "quality_score": 2}],
        "dropped": [],
    })

    responses = {
        "curate": curate_response,
        "dual_tldr": json.dumps({
            "ceo": [{"bullet": "MAS guidance signals tighter AI governance", "url": "https://x/r1", "action": "Escalate to Legal"},
                    {"bullet": "GPT-5 launch shifts competitive landscape", "url": "https://x/m1", "action": "Brief CTO"},
                    {"bullet": "Competitor launches AI underwriting", "url": "https://x/b1", "action": "Monitor"}],
            "cto": [{"bullet": "Critical prompt injection affects enterprise agents", "url": "https://x/s1", "action": "Alert team"},
                    {"bullet": "GPT-5 adds 200k context and native tool streaming", "url": "https://x/m1", "action": "Evaluate this sprint"},
                    {"bullet": "New RAG framework beats BM25 by 35%", "url": "https://x/f1", "action": "Try today"}],
        }),
        "model_release": json.dumps([{"url": "https://x/m1", "vendor": "OpenAI", "model_name": "GPT-5",
                                       "key_upgrade": "200k context and tool streaming",
                                       "context_window": "200000", "pricing_change": "-15% input",
                                       "aia_use_case": "Claims document review at scale"}]),
        "security": json.dumps([{"url": "https://x/s1", "severity": "critical",
                                  "attack_vector": "prompt injection via tool output",
                                  "affected_systems": "LangGraph, CrewAI agent frameworks",
                                  "mitigation": "Sandbox tool outputs; never interpolate into system prompt",
                                  "aia_relevance": "direct"}]),
        "framework": json.dumps([{"url": "https://x/f1", "replaces_or_extends": "LangChain",
                                   "primary_language": "Python", "use_case": "RAG pipeline",
                                   "adoption_signal": "production-ready", "try_today": "yes",
                                   "aia_fit": "Claims document retrieval pipeline"}]),
        "eval": json.dumps([{"url": "https://x/e1", "item_type": "benchmark",
                              "models_tested": ["GPT-4o", "Claude 3.5"], "task_type": "enterprise QA",
                              "key_finding": "Hybrid retrieval beats vector-only by 35%",
                              "winner": "BM25 + dense hybrid", "aia_takeaway": "Switch retrieval before next RAG build",
                              "concept_name": None, "what_it_does": None, "practical_horizon": None}]),
        "enterprise": json.dumps([{"url": "https://x/e1", "story_type": "success",
                                    "industry": "banking", "use_case": "Compliance review",
                                    "outcome": "Cut review time by 60% using GenAI + human-in-loop",
                                    "replicable_at_aia": "yes",
                                    "lesson": "RAG on policy docs with human exceptions delivers reliable results"}]),
        "regulatory": json.dumps([{"url": "https://x/r1", "instrument_type": "guidance",
                                    "jurisdiction": "Singapore/MAS", "deadline": "2026-06-30",
                                    "aia_action": "Legal and Risk team should review and prepare response",
                                    "urgency": "act"}]),
        "boardroom": json.dumps([{"url": "https://x/b1", "sentence": "Boardroom note for AIA."}]),
        "emerging": json.dumps([{"url": "https://x/c1", "concept_name": "Compound AI",
                                  "tech_explanation": "Combines multiple specialized models in a pipeline. Each handles what it does best.",
                                  "business_implication": "Better AI outcomes without needing the largest model.",
                                  "maturity": "early-adoption", "horizon": "6-12 months"}]),
        "heatmap": json.dumps({"openai": "Released GPT-5 with multimodal reasoning.", "google": None,
                               "anthropic": None, "meta": None, "mistral": None, "xai": None}),
        "steal": json.dumps({"title": "AI Claims Triage Bot", "what": "Build an LLM triage tool.",
                             "why_now": "GPT-5 makes this feasible today.", "domain": "claims",
                             "effort": "weeks", "team": "Digital & Technology", "confidence": "high"}),
        "editors_take": "OpenAI's GPT-5 launch fundamentally shifts what enterprise AI teams can build today.",
        "week_review": "This week GenAI disrupted insurance underwriting at scale.",
    }

    def _invoke(prompt: str):
        p = prompt.lower()
        key = (
            "curate"      if "curate" in p or "categorise" in p or "insurtech" in p else
            "dual_tldr"   if "for your ceo" in p or "for your cto" in p else
            "model_release" if "capability card" in p or "key_upgrade" in p else
            "security"    if "attack_vector" in p or "ciso" in p else
            "framework"   if "try_today" in p or "replaces_or_extends" in p else
            "eval"        if "key_finding" in p or "models_tested" in p else
            "enterprise"  if "story_type" in p or "replicable_at_aia" in p else
            "regulatory"  if "instrument_type" in p or "jurisdiction" in p else
            "boardroom"   if "boardroom" in p else
            "emerging"    if "concept_name" in p or "tech_explanation" in p else
            "heatmap"     if "ai labs" in p or ("openai" in p and "google" in p and "anthropic" in p) else
            "steal"       if "steal" in p or "product idea" in p else
            "editors_take" if "intelligence brief" in p or "opening 2-3" in p else
            "week_review"  if "week in review" in p or "defining theme" in p else
            "curate"
        )
        m = MagicMock()
        m.content = responses.get(key, "{}")
        return m

    fake = MagicMock()
    fake.invoke.side_effect = _invoke
    for target in (
        "src.llm.get_llm",
        "src.nodes.curate_node.get_llm",
        "src.nodes.summarize_node.get_llm",
    ):
        monkeypatch.setattr(target, lambda temperature=0.2: fake)
    return fake
