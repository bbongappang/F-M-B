from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import random
from .optimizer import Decision

@dataclass
class Telemetry:
    latency_ms: float
    loss_pct: float
    jitter_ms: float
    coverage_ok: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def execute(decision: Decision) -> Telemetry:
    """
    Back에서 실행된 후 관측되는 telemetry(데모 시뮬).
    """
    base_latency = random.uniform(18, 35)
    base_loss = random.uniform(0.8, 3.5)
    base_jitter = random.uniform(5, 25)

    # 기대 gain 반영(개선)
    lat = max(3.0, base_latency - decision.expected_gain["latency_ms"])
    loss = max(0.05, base_loss - decision.expected_gain["loss_pct"])
    jit = max(0.5, base_jitter - decision.expected_gain["jitter_ms"])

    coverage_ok = True if decision.ris_active else random.choice([True, True, False])

    return Telemetry(
        latency_ms=round(lat, 2),
        loss_pct=round(loss, 2),
        jitter_ms=round(jit, 2),
        coverage_ok=coverage_ok,
    )
