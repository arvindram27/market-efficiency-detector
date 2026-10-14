"""Optional real intraday market data via yfinance (free, no key).

This is the "live" counterpart to the synthetic generator. It is intentionally
kept out of the core dependency graph: yfinance (and pandas) are imported lazily
so the vertical slice runs with zero extra installs.

NSE tickers use the ``.NS`` suffix (e.g. ``RELIANCE.NS``), SGX the ``.SI`` suffix
(e.g. ``D05.SI``). Intraday history is limited by the provider (~7 days at 1m),
which is why the synthetic path is the deterministic default for tests and demos.
"""
from __future__ import annotations

from datetime import datetime, timezone

from med.types import PriceBar


def fetch_intraday(
    ticker: str,
    *,
    interval: str = "5m",
    period: str = "5d",
) -> list[PriceBar]:
    """Fetch intraday OHLCV bars and normalize to ``list[PriceBar]``.

    Raises ``ImportError`` if yfinance is not installed; returns ``[]`` on a
    provider/network failure (graceful degradation — a missed fetch, not a crash).
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "yfinance is required for the live data path. Install it with "
            "`pip install yfinance` (or `pip install -e '.[live]'`)."
        ) from exc

    df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return []

    bars: list[PriceBar] = []
    for ts, row in df.iterrows():
        # Normalize to tz-aware UTC regardless of provider tz.
        t = ts.to_pydatetime()
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        bars.append(
            PriceBar(
                ts=t.astimezone(timezone.utc),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0.0) or 0.0),
            )
        )
    return bars
