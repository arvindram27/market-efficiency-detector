from __future__ import annotations

import pytest

from med.config import MedConfig
from med.data.synthetic import build_demo_scenarios


@pytest.fixture(scope="session")
def config() -> MedConfig:
    return MedConfig()


@pytest.fixture(scope="session")
def scenarios(config):
    return {s.name: s for s in build_demo_scenarios(config)}
