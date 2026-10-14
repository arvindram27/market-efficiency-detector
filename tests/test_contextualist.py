from __future__ import annotations

from med.agents import contextualist
from med.types import EventType, NewsWeight


def test_classify_earnings():
    assert contextualist.classify_event("Acme Q3 earnings beat estimates") == EventType.EARNINGS


def test_classify_merger():
    assert contextualist.classify_event("Acme to merge with Beta Corp in a USD 2B deal") == EventType.M_A


def test_classify_macro():
    assert contextualist.classify_event("RBI announces interest rate hike") == EventType.MACRO


def test_classify_other():
    assert contextualist.classify_event("Acme launches a new website") == EventType.OTHER


def test_news_weight_high_for_tradeable():
    assert (
        contextualist.news_weight("Acme Q3 earnings beat estimates, profit up 40%", EventType.EARNINGS)
        == NewsWeight.HIGH
    )


def test_news_weight_low_for_other():
    assert contextualist.news_weight("random text here", EventType.OTHER) == NewsWeight.LOW


def test_sentiment_sign_positive_and_negative():
    assert contextualist.sentiment_score("profit soars to a record high on strong growth") > 0
    assert contextualist.sentiment_score("losses widen as revenue plunges") < 0
