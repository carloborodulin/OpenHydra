from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# tests/ -> warehouse/ -> OpenHydra/  ->  data/samples
SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


@pytest.fixture
def sample() -> Callable[[str], Any]:
    def _load(name: str) -> Any:
        return json.loads((SAMPLES / f"{name}.json").read_text())

    return _load
