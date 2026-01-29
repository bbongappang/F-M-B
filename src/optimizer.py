from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
from .middle import Constraints, Intent

@dataclass
class Decision:
    slice_id: str
    ris_zone: str
    ris_active: bool
    ai_ran_mode: str
    expected_gain: Dict[str, float]  # latency/loss/jitter improvements (demo)
    expected_cost: Dict[str, float]  # energy/ops cost (demo)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def decide(intent: Intent, c: Constraints) -> Decision:
    """
    ✅ 최종 결정 주체(규칙/최적화). ML은 제약만 제공.
    """
    # Slice 선택(규칙)
    if intent.context == "EMERGENCY_CRITICAL":
        slice_id = "URLLC"
        ai_ran_mode = "Aggressive"
    elif intent.context == "EMERGENCY_SUSPECT":
        slice_id = "URLLC"
        ai_ran_mode = "Assist"
    else:
        slice_id = "eMBB"
        ai_ran_mode = "Baseline"

    # Selective RIS 트리거: uncertainty + cost-weight 균형(아주 단순)
    cost_weight = float(c.penalty_weights.get("cost", 0.3))
    ris_active = (c.uncertainty >= 0.6) and (cost_weight <= 0.25)
    ris_zone = "Zone_B3" if ris_active else "OFF"

    # 예상 효과(데모용)
    expected_gain = {
        "latency_ms": 12.0 if slice_id == "URLLC" else 2.0,
        "loss_pct": 1.5 if ris_active else 0.4,
        "jitter_ms": 10.0 if ai_ran_mode != "Baseline" else 2.0,
    }
    expected_cost = {
        "energy": 12.0 if ris_active else 1.0,
        "ops": 8.0 if ai_ran_mode == "Aggressive" else (4.0 if ai_ran_mode == "Assist" else 1.0),
    }

    return Decision(
        slice_id=slice_id,
        ris_zone=ris_zone,
        ris_active=ris_active,
        ai_ran_mode=ai_ran_mode,
        expected_gain=expected_gain,
        expected_cost=expected_cost,
    )
