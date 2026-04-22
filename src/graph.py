from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.rss_node import rss_node
from src.nodes.arxiv_node import arxiv_node
from src.nodes.github_node import github_node
from src.nodes.hf_node import hf_node
from src.nodes.hn_node import hn_node
from src.nodes.reddit_node import reddit_node
from src.nodes.youtube_node import youtube_node
from src.nodes.aggregate_node import aggregate_node
from src.nodes.curate_node import curate_node
from src.nodes.summarize_node import summarize_node
from src.nodes.email_node import email_node


def build_graph():
    g = StateGraph(AgentState)

    fetchers = [
        ("rss", rss_node),
        ("arxiv", arxiv_node),
        ("github", github_node),
        ("hf", hf_node),
        ("hn", hn_node),
        ("reddit", reddit_node),
        ("youtube", youtube_node),
    ]
    for name, fn in fetchers:
        g.add_node(name, fn)

    g.add_node("aggregate", aggregate_node)
    g.add_node("curate", curate_node)
    g.add_node("summarize", summarize_node)
    g.add_node("email", email_node)

    for name, _ in fetchers:
        g.add_edge(START, name)
        g.add_edge(name, "aggregate")

    g.add_edge("aggregate", "curate")
    g.add_edge("curate", "summarize")
    g.add_edge("summarize", "email")
    g.add_edge("email", END)

    return g.compile()
