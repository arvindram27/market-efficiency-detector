"""CLI demo: run the PAL vertical slice end-to-end and print a report.

Usage (from the project root):  python -m med.demo
"""
from __future__ import annotations

from med.config import MedConfig
from med.data.synthetic import build_demo_scenarios
from med.pipeline import Pipeline
from med.provenance import current_git_sha
from med.storage.sqlite_store import PalStore

_DISCLAIMER = (
    "DISCLAIMER: research prototype only. Signals are paper-traded; past simulated\n"
    "performance is not indicative of future results; not investment advice."
)


def _fmt_minutes(seconds: float | None) -> str:
    if seconds is None:
        return "--"
    return f"{seconds / 60:.1f}"


def main() -> None:
    config = MedConfig()
    scenarios = build_demo_scenarios(config)
    store = PalStore("data/med.db")
    pipeline = Pipeline(config=config, store=store)
    sha = current_git_sha() or "n/a (not a git repo)"

    line = "=" * 78
    print(line)
    print(" MARKET EFFICIENCY DETECTOR (MED) - Price Adjustment Latency - vertical slice")
    print(line)
    print(f" git SHA: {sha}  |  vintage: synthetic-v0.1  |  tier: MID")
    print(line)
    print(f" {'Scenario':<10} {'Type':<10} {'wght':<5} {'z-score':>8} {'PAL (min)':>9} {'Class':<13}")
    print(" " + "-" * 76)

    for s in scenarios:
        result = pipeline.run(
            s.news_event, s.bars, tier=s.tier.value, seed=s.seed, vintage="synthetic-v0.1"
        )
        pe = result.pal_event
        # A suppressed (gate-failed) event has no meaningful PAL; show it as blank.
        pal = "--" if not result.gate.trigger_passed else _fmt_minutes(pe.pal_seconds)
        print(
            f" {s.name:<10} {pe.event_type.value:<10} {pe.news_weight.value:<5} "
            f"{pe.z_score:>8.2f} {pal:>9} {pe.pal_class.value:<13}"
        )

    print(" " + "-" * 76)
    print(f" Saved {store.count()} pal_event(s) to {store.path}")
    print()
    print(_DISCLAIMER)
    store.close()


if __name__ == "__main__":
    main()
