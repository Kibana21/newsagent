from __future__ import annotations
from typing import Dict, List, TypedDict


class NewsItem(TypedDict, total=False):
    title: str
    url: str
    summary: str
    source: str           # "tavily" | "rss" | "arxiv" | "github" | "huggingface" | "hackernews" | "reddit" | "youtube"
    published_at: str     # ISO 8601
    insurance_score: int  # 1 (low) | 2 (medium) | 3 (high); default 1 until Phase 3
    competitor: bool      # default False until Phase 3
    regulatory: bool      # default False until Phase 3
    buzz_score: int       # count of sources the item appeared in; default 1 until Phase 3


class CategorizedNews(TypedDict, total=False):
    business: List[NewsItem]
    technical: List[NewsItem]
    research: List[NewsItem]
    insurtech: List[NewsItem]


class EmailLog(TypedDict, total=False):
    status: str           # "success" | "failed"
    subscribers_found: int
    emails_sent: int
    errors: List[str]


class AgentState(TypedDict, total=False):
    search_query: str
    days: int

    tavily_news: List[NewsItem]
    rss_news: List[NewsItem]
    arxiv_news: List[NewsItem]
    github_news: List[NewsItem]
    hf_news: List[NewsItem]
    hn_news: List[NewsItem]
    reddit_news: List[NewsItem]
    youtube_news: List[NewsItem]

    raw_news: List[NewsItem]
    buzz_scores: Dict[str, int]
    curated_news: List[NewsItem]
    categorized_news: CategorizedNews

    final_report: str
    email_log: EmailLog
    mode: str             # "daily" | "monthly"
