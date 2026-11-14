"""Versioned, plain-Python mt1 input types. No legacy schema changes."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

@dataclass(frozen=True)
class Bar:
    open_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    available_ts: Optional[datetime] = None

@dataclass(frozen=True)
class Study:
    publication: datetime
    headline: str
    ticker: str
    study_id: str
    source_url: str
    data_vintage: str
    input_sha256: str
    source_revision: Optional[str] = None
    receipt: Optional[datetime] = None
    retrieval: Optional[datetime] = None
    interval_seconds: int = 60
    pre_bars: int = 60
    move_seconds: int = 300
    observation_seconds: int = 5400
    reference_start_seconds: int = 4200
    reference_end_seconds: int = 5400
    z_threshold: float = 2.0
    band_sigma_mult: float = 0.5
    consecutive_bars: int = 5

# Serialization order is explicit. Nested values have their own fixed shapes.
RESULT_FIELDS: Tuple[str, ...] = (
    'schema_version', 'study_id', 'ticker', 'source_url', 'exact_headline',
    'data_vintage', 'input_sha256', 'algorithm_version', 'source_revision',
    'parameters', 'time_context', 'coverage_status', 'coverage_missing_by_role',
    'gate_status', 'gate_reason', 'gate_direction', 'reference_status',
    'stabilization_status', 'result_information_status', 'sigma_pre', 'z_score',
    'reference_price', 'event_type', 'news_weight', 'reference_bar_count',
    'candidate_bar_count', 'candidate_bar_open_ts', 'candidate_bar_close_ts',
    'confirmation_bar_open_ts', 'confirmation_bar_close_ts',
    'candidate_close_delay_seconds', 'confirmation_close_delay_seconds',
    'reference_close_lower_bound_ts', 'result_available_lower_bound_ts',
    'result_available_ts', 'required_input_roles', 'availability_assumption')
