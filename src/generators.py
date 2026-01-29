from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from .schema import RawIngest, SourceType, now_iso

def _rid() -> str:
    return f"raw-{uuid.uuid4().hex[:8]}"

def gen_nurse_note(patient_id: str = "A") -> RawIngest:
    note = random.choice([
        "환자 숨 가쁨, 피부 창백, 손발 차가움",
        "호흡 곤란 호소. 산소포화도 측정 필요",
        "흉통 호소. 불안정한 모습.",
        "청색증 의심. 즉시 확인 요청.",
    ])
    payload = f"NURSE_NOTE[{patient_id}]: \"{note}\""
    return RawIngest(raw_id=_rid(), source="nurse_note", ingest_time=now_iso(), payload=payload)

def gen_wearable_spike(patient_id: str = "A") -> RawIngest:
    hr = random.randint(120, 170)
    spo2 = random.randint(82, 92)
    noise = round(random.uniform(0.05, 0.20), 2)
    payload = f"ECG: {hr}bpm, SpO2={spo2}%, noise={noise}"
    return RawIngest(raw_id=_rid(), source="wearable", ingest_time=now_iso(), payload=payload)

def gen_ambulance_app(patient_id: str = "A") -> RawIngest:
    payload: Dict[str, Any] = {
        "patient": patient_id,
        "fall_detected": random.choice([True, False]),
        "location": random.choice(["ER_gate", "Corridor_B3", "ICU_entry"]),
        "confidence": round(random.uniform(0.6, 0.95), 2),
        "note": random.choice(["이동 중", "산소 공급 중", "의식 저하 의심"]),
    }
    return RawIngest(raw_id=_rid(), source="ambulance_app", ingest_time=now_iso(), payload=payload)

def gen_network_degradation(patient_id: str = "A") -> RawIngest:
    payload = {
        "link": random.choice(["wifi-ward", "private5g-b3", "uplink-core"]),
        "rssi": random.randint(-92, -65),
        "loss_pct": round(random.uniform(0.5, 4.0), 2),
        "jitter_ms": round(random.uniform(2.0, 30.0), 1),
        "scope": f"patient_{patient_id}",
    }
    return RawIngest(raw_id=_rid(), source="network", ingest_time=now_iso(), payload=payload)
