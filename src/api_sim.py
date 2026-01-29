from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import time
import uuid

@dataclass
class ApiCall:
    method: str
    path: str
    body: Dict[str, Any]
    response: Dict[str, Any]

def post(path: str, body: Dict[str, Any], delay_ms: int = 250) -> ApiCall:
    time.sleep(delay_ms / 1000.0)  # "적용 시간" 연출
    resp = {
        "request_id": f"req-{uuid.uuid4().hex[:8]}",
        "applied": True,
        "eta_sec": round(delay_ms / 1000.0, 2),
    }
    return ApiCall(method="POST", path=path, body=body, response=resp)

def apply_network(slice_payload: Dict[str, Any]) -> ApiCall:
    return post("/network/slice/apply", slice_payload, delay_ms=220)

def apply_ris(ris_payload: Dict[str, Any]) -> ApiCall:
    return post("/ris/zone/activate", ris_payload, delay_ms=180)

def apply_ai_ran(ai_payload: Dict[str, Any]) -> ApiCall:
    return post("/ai-ran/policy/update", ai_payload, delay_ms=260)
