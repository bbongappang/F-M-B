from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

SourceType = Literal["wearable", "nurse_note", "ambulance_app", "network"]

@dataclass
class RawIngest:
    raw_id: str
    source: SourceType
    ingest_time: str
    payload: Any  # 자유형(문자열/딕트/리스트 등)

@dataclass
class StandardEvent:
    event_id: str
    source: SourceType
    patient_id: str
    event_time: str
    ingest_time: str
    signal: List[str]
    severity: float
    confidence: float
    embedding: List[float]
    payload_hint: Dict[str, float]  # sizes
    ttl_sec: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
