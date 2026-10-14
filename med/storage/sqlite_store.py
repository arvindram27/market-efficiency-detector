"""SQLite persistence — the free local stand-in for Snowflake.

Stores `pal_events` rows with the PRD §4.4 contract fields plus provenance
(vintage, seed, git sha). The schema is deliberately measurement-only; the
`signals` table arrives in v2.5 without a migration here.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from med.types import (
    EventClassification,
    EventType,
    NewsWeight,
    PALEvent,
    Tier,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pal_events (
    event_id          TEXT PRIMARY KEY,
    ticker            TEXT NOT NULL,
    tier              TEXT NOT NULL,
    t_event           TEXT NOT NULL,
    t_efficient       TEXT,
    pal_seconds       REAL,
    pal_class         TEXT NOT NULL,
    z_score           REAL NOT NULL,
    sigma_pre         REAL NOT NULL,
    equilibrium_price REAL,
    sentiment_score   REAL NOT NULL,
    event_type        TEXT NOT NULL,
    news_weight       TEXT NOT NULL,
    data_vintage      TEXT NOT NULL,
    generator_seed    INTEGER,
    git_sha           TEXT,
    created_at        TEXT NOT NULL
);
"""

_COLUMNS = (
    "event_id", "ticker", "tier", "t_event", "t_efficient", "pal_seconds",
    "pal_class", "z_score", "sigma_pre", "equilibrium_price", "sentiment_score",
    "event_type", "news_weight", "data_vintage", "generator_seed", "git_sha",
    "created_at",
)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s)


class PalStore:
    def __init__(self, path: str = "data/med.db"):
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save(self, event: PALEvent) -> None:
        row = (
            event.event_id,
            event.ticker,
            event.tier.value,
            _iso(event.t_event),
            _iso(event.t_efficient),
            event.pal_seconds,
            event.pal_class.value,
            event.z_score,
            event.sigma_pre,
            event.equilibrium_price,
            event.sentiment_score,
            event.event_type.value,
            event.news_weight.value,
            event.data_vintage,
            event.generator_seed,
            event.git_sha,
            _iso(datetime.now(timezone.utc)),
        )
        placeholders = ", ".join("?" for _ in _COLUMNS)
        self._conn.execute(
            f"INSERT OR REPLACE INTO pal_events ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
            row,
        )
        self._conn.commit()

    def list_all(self) -> list[PALEvent]:
        rows = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM pal_events ORDER BY created_at"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM pal_events").fetchone()[0])

    @staticmethod
    def _from_row(r: tuple) -> PALEvent:
        (
            event_id, ticker, tier, t_event, t_efficient, pal_seconds, pal_class,
            z_score, sigma_pre, equilibrium_price, sentiment_score, event_type,
            news_weight, data_vintage, generator_seed, git_sha, _created_at,
        ) = r
        return PALEvent(
            event_id=event_id,
            ticker=ticker,
            tier=Tier(tier),
            t_event=_parse_iso(t_event),
            t_efficient=_parse_iso(t_efficient),
            pal_seconds=pal_seconds,
            pal_class=EventClassification(pal_class),
            z_score=z_score,
            sigma_pre=sigma_pre,
            equilibrium_price=equilibrium_price,
            sentiment_score=sentiment_score,
            event_type=EventType(event_type),
            news_weight=NewsWeight(news_weight),
            data_vintage=data_vintage,
            generator_seed=generator_seed,
            git_sha=git_sha,
        )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PalStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
