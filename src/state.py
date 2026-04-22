from __future__ import annotations
from typing import Dict, List, TypedDict


class NewsItem(TypedDict, total=False):
    title: str
    url: str
    summary: str
    source: str           # "rss"|"arxiv"|"github"|"huggingface"|"hackernews"|"reddit"|"youtube"
    published_at: str     # ISO 8601
    insurance_score: int  # 1 (low) | 2 (medium) | 3 (high)
    competitor: bool      # True if mentions a competitor insurer
    regulatory: bool      # True if mentions MAS/IMDA/HKIA/OJK
    buzz_score: int       # count of sources the item appeared in
    action_signal: str    # "act" | "watch" | "aware"
    sentiment: str        # "opportunity" | "risk" | "neutral"
    quality_score: int    # 1 (low) | 2 (medium) | 3 (high) — signal quality
    severity: str         # "critical"|"high"|"medium"|"info" — security items only
    topic_pack: str       # which SERP query pack sourced this item


class CategorizedNews(TypedDict, total=False):
    business: List[NewsItem]
    models: List[NewsItem]
    frameworks: List[NewsItem]
    security: List[NewsItem]
    research: List[NewsItem]
    enterprise: List[NewsItem]
    regulatory: List[NewsItem]
    insurtech: List[NewsItem]
    emerging: List[NewsItem]


class EmailLog(TypedDict, total=False):
    status: str           # "success" | "failed"
    subscribers_found: int
    emails_sent: int
    errors: List[str]


class AgentState(TypedDict, total=False):
    search_query: str
    days: int

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

    final_report: str     # combined (full) report
    dev_report: str       # developer-focused report
    biz_report: str       # business-focused report
    email_log: EmailLog
    mode: str             # "daily" | "monthly"
