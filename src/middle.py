from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List
import random

from .schema import StandardEvent

@dataclass
class Constraints:
    latency_budget_ms: int
    reliability_target: float
    penalty_weights: Dict[str, float]  # latency/loss/cost
    uncertainty: float  # "불확실성" 지표(Selective RIS 트리거)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Intent:
    intent_type: str
    patient_id: str
    context: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def build_context(ev: StandardEvent) -> str:
    if ev.severity >= 0.82:
        return "EMERGENCY_CRITICAL"
    if ev.severity >= 0.7:
        return "EMERGENCY_SUSPECT"
    return "NORMAL_MONITORING"

def ml_generate_constraints(ev: StandardEvent) -> Constraints:
    """
    ✅ ML 역할: 제약 파라미터(임계값/상하한/벌점 가중치) 생성/갱신
    ❌ ML이 자원 할당 결정을 내리면 안 됨
    """
    context = build_context(ev)

    if context == "EMERGENCY_CRITICAL":
        latency = 8
        reliab = 0.99999
        w = {"latency": 0.55, "loss": 0.30, "cost": 0.15}
        uncertainty = round(random.uniform(0.65, 0.9), 2)
    elif context == "EMERGENCY_SUSPECT":
        latency = 12
        reliab = 0.9999
        w = {"latency": 0.45, "loss": 0.30, "cost": 0.25}
        uncertainty = round(random.uniform(0.45, 0.75), 2)
    else:
        latency = 40
        reliab = 0.999
        w = {"latency": 0.20, "loss": 0.20, "cost": 0.60}
        uncertainty = round(random.uniform(0.10, 0.35), 2)

    return Constraints(
        latency_budget_ms=latency,
        reliability_target=reliab,
        penalty_weights=w,
        uncertainty=uncertainty,
    )

def make_intent(ev: StandardEvent) -> Intent:
    context = build_context(ev)
    if context.startswith("EMERGENCY"):
        itype = "emergency_care"
    else:
        itype = "routine_monitoring"
    return Intent(intent_type=itype, patient_id=ev.patient_id, context=context)
