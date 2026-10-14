"""Contextualist agent — the linguistic half of event detection.

Offline, deterministic, LLM-free (an LLM-backed version is the v2 upgrade).
Uses VADER for sentiment when installed and a tiny built-in lexicon otherwise,
plus keyword taxonomy for event type and a news-weight heuristic (PRD §2.3).
"""
from __future__ import annotations

from med.types import ContextualResult, EventType, NewsEvent, NewsWeight

_EVENT_KEYWORDS: dict[EventType, tuple[str, ...]] = {
    EventType.EARNINGS: (
        "earnings", "profit", "revenue", "quarter", "q1", "q2", "q3", "q4",
        "results", "guidance", "net profit", "eps", "outlook", "beat", "miss",
    ),
    EventType.MACRO: (
        "rbi", "fed", "interest rate", "rate hike", "rate cut", "inflation",
        "gdp", "cpi", "policy", "budget", "fiscal", "monetary", "reserve bank",
    ),
    EventType.M_A: (
        "acquisition", "acquires", "acquire", "merger", "merges", "takeover",
        "buyout", "stake", "deal", "combine", "combines",
    ),
}

_POSITIVE = {
    "beat", "beats", "up", "gain", "gains", "growth", "surge", "record", "strong",
    "profit", "increase", "rises", "positive", "outperform", "boost", "win", "wins",
}
_NEGATIVE = {
    "miss", "misses", "down", "loss", "losses", "decline", "drop", "drops", "weak",
    "plunge", "cut", "cuts", "negative", "underperform", "fall", "falls", "warns",
}


def classify_event(headline: str) -> EventType:
    h = headline.lower()
    for event_type, keywords in _EVENT_KEYWORDS.items():
        if any(k in h for k in keywords):
            return event_type
    return EventType.OTHER


def sentiment_score(headline: str) -> float:
    """Compound sentiment in [-1, 1]. VADER if available, else a built-in lexicon."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        return float(SentimentIntensityAnalyzer().polarity_scores(headline)["compound"])
    except Exception:
        return _fallback_sentiment(headline)


def _fallback_sentiment(headline: str) -> float:
    words = set(headline.lower().split())
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def news_weight(headline: str, event_type: EventType) -> NewsWeight:
    if event_type == EventType.OTHER:
        return NewsWeight.LOW
    if len(headline.strip().split()) < 3:
        return NewsWeight.LOW
    return NewsWeight.HIGH


def analyze(news_event: NewsEvent) -> ContextualResult:
    event_type = classify_event(news_event.headline)
    weight = news_weight(news_event.headline, event_type)
    sentiment = sentiment_score(news_event.headline)
    return ContextualResult(event_type=event_type, news_weight=weight, sentiment=sentiment)
