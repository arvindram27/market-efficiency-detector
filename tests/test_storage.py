from __future__ import annotations

from med.pipeline import Pipeline
from med.storage.sqlite_store import PalStore
from med.types import EventClassification


def test_pal_store_round_trip(scenarios, tmp_path):
    db = str(tmp_path / "med.db")
    store = PalStore(db)

    pipeline = Pipeline(store=store)
    res = pipeline.run(
        scenarios["fast"].news_event,
        scenarios["fast"].bars,
        tier=scenarios["fast"].tier.value,
        seed=scenarios["fast"].seed,
    )
    original = res.pal_event

    assert store.count() == 1
    rows = store.list_all()
    assert len(rows) == 1

    reloaded = rows[0]
    assert reloaded.event_id == original.event_id
    assert reloaded.ticker == original.ticker
    assert reloaded.tier == original.tier
    assert reloaded.t_event == original.t_event
    assert reloaded.t_efficient == original.t_efficient
    assert reloaded.pal_seconds == original.pal_seconds
    assert reloaded.pal_class == original.pal_class == EventClassification.FAST
    assert reloaded.event_type == original.event_type
    assert reloaded.news_weight == original.news_weight
    assert reloaded.generator_seed == original.generator_seed
    assert reloaded.data_vintage == original.data_vintage
    store.close()
