from __future__ import annotations

from med.agents import decision_maker
from med.types import Direction, EventType, NewsWeight


def test_gate_passes_when_all_conditions_met():
    gate = decision_maker.evaluate_gate(
        z_score=3.0, event_type=EventType.EARNINGS, news_weight=NewsWeight.HIGH, z_threshold=2.0
    )
    assert gate.trigger_passed is True
    assert gate.direction == Direction.LONG


def test_gate_suppressed_low_confidence():
    gate = decision_maker.evaluate_gate(
        z_score=3.0, event_type=EventType.EARNINGS, news_weight=NewsWeight.LOW, z_threshold=2.0
    )
    assert gate.trigger_passed is False
    assert gate.suppressed_reason == "LOW_CONF"


def test_gate_suppressed_event_type():
    gate = decision_maker.evaluate_gate(
        z_score=3.0, event_type=EventType.OTHER, news_weight=NewsWeight.HIGH, z_threshold=2.0
    )
    assert gate.trigger_passed is False
    assert gate.suppressed_reason == "EVENT_TYPE"


def test_gate_suppressed_no_price_move():
    gate = decision_maker.evaluate_gate(
        z_score=1.0, event_type=EventType.EARNINGS, news_weight=NewsWeight.HIGH, z_threshold=2.0
    )
    assert gate.trigger_passed is False
    assert gate.suppressed_reason == "NO_PRICE_MOVE"


def test_short_direction_for_negative_move():
    gate = decision_maker.evaluate_gate(
        z_score=-3.0, event_type=EventType.MACRO, news_weight=NewsWeight.HIGH, z_threshold=2.0
    )
    assert gate.trigger_passed is True
    assert gate.direction == Direction.SHORT
