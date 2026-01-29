from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from .back import Telemetry
from .optimizer import Decision
from .middle import Intent, Constraints

@dataclass
class KOI:
    mission_success: int     # 0~100
    operational_cost: int    # 0~100 (높을수록 "저비용"으로 정의)
    stability: int           # 0~100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def koi_from(tele: Telemetry, decision: Decision, c: Constraints, intent: Intent) -> KOI:
    # Mission: 지연/손실/커버리지 기반 단순 점수
    ms = 100
    ms -= int(max(0, (tele.latency_ms - c.latency_budget_ms) * 2))
    ms -= int(tele.loss_pct * 8)
    if not tele.coverage_ok:
        ms -= 15
    ms = max(0, min(100, ms))

    # Cost: 에너지/운영비 proxy를 0~100로 역점수(높을수록 좋음)
    energy = decision.expected_cost["energy"]
    ops = decision.expected_cost["ops"]
    cost_penalty = energy * 2 + ops * 2
    oc = max(0, min(100, int(100 - cost_penalty)))

    # Stability: aggressive면 안정성↓, 변화가 큰 상황이면↓ (데모용)
    st = 90
    if decision.ai_ran_mode == "Aggressive":
        st -= 20
    st -= int(c.uncertainty * 15)
    st = max(0, min(100, st))

    return KOI(mission_success=ms, operational_cost=oc, stability=st)

def effect_mapping(decision: Decision) -> List[Dict[str, str]]:
    cards = []
    if decision.ris_active:
        cards.append({"cause": f"Selective RIS ON ({decision.ris_zone})", "effect": "Packet loss ↓ / Coverage ↑"})
    else:
        cards.append({"cause": "RIS remains Passive", "effect": "Energy cost ↓ (no active boost)"})

    if decision.ai_ran_mode != "Baseline":
        cards.append({"cause": f"AI-RAN {decision.ai_ran_mode}", "effect": "Latency jitter ↓ / Scheduling 안정화"})
    else:
        cards.append({"cause": "AI-RAN Baseline", "effect": "운영 개입 최소화(Ops cost ↓)"})

    if decision.slice_id == "URLLC":
        cards.append({"cause": "URLLC Slice Applied", "effect": "Latency budget 만족률 ↑ / Reliability ↑"})
    else:
        cards.append({"cause": "eMBB Slice Applied", "effect": "비용 효율 ↑ (routine monitoring)"})

    return cards
