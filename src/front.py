from __future__ import annotations
import re
import uuid
import random
from collections import deque
from typing import Any, Deque, Dict, List, Tuple
from .schema import RawIngest, StandardEvent, now_iso

def fake_embedding(dim: int = 8) -> List[float]:
    # 실제 임베딩 대신 데모용(경량화 시각화 목적)
    return [round(random.uniform(-1, 1), 2) for _ in range(dim)]

def estimate_sizes(payload: Any) -> Tuple[float, float]:
    # 매우 단순한 size 추정(데모용)
    raw_str = str(payload)
    raw_kb = max(0.1, len(raw_str) / 1024.0)
    packed_kb = max(0.05, raw_kb * 0.08)  # "벡터화/경량화" 연출
    return round(raw_kb, 2), round(packed_kb, 2)

def normalize(raw: RawIngest, patient_id_default: str = "A") -> StandardEvent:
    payload = raw.payload
    signals: List[str] = []
    patient_id = patient_id_default

    if raw.source == "wearable":
        # "ECG: 142bpm, SpO2=88%, noise=0.12"
        m_hr = re.search(r"(\d+)bpm", str(payload))
        m_spo2 = re.search(r"SpO2=(\d+)", str(payload))
        hr = int(m_hr.group(1)) if m_hr else 90
        spo2 = int(m_spo2.group(1)) if m_spo2 else 97
        if hr >= 130:
            signals.append("tachycardia")
        if spo2 <= 90:
            signals.append("spo2_drop")

    elif raw.source == "nurse_note":
        txt = str(payload)
        if "청색증" in txt or "푸르" in txt:
            signals.append("cyanosis_suspect")
        if "호흡" in txt or "숨" in txt:
            signals.append("dyspnea_suspect")
        if "흉통" in txt:
            signals.append("chest_pain_suspect")
        # NURSE_NOTE[A] 형태면 patient 추출
        m = re.search(r"NURSE_NOTE\[(\w+)\]", txt)
        if m:
            patient_id = m.group(1)

    elif raw.source == "ambulance_app":
        if isinstance(payload, dict):
            patient_id = payload.get("patient", patient_id_default)
            if payload.get("fall_detected"):
                signals.append("fall_detected")
            loc = payload.get("location", "")
            if "Corridor" in loc or "ER" in loc:
                signals.append("in_motion_or_transfer")

    elif raw.source == "network":
        if isinstance(payload, dict):
            if payload.get("loss_pct", 0) >= 2.0:
                signals.append("packet_loss_rising")
            if payload.get("jitter_ms", 0) >= 15.0:
                signals.append("jitter_rising")

    if not signals:
        signals = ["normal_observation"]

    # severity/confidence(데모용): signals 기반으로 단순 생성
    severity = 0.2
    if any(s in signals for s in ["spo2_drop", "tachycardia", "cyanosis_suspect", "packet_loss_rising", "jitter_rising"]):
        severity = 0.75
    if any(s in signals for s in ["chest_pain_suspect", "fall_detected"]):
        severity = max(severity, 0.82)

    confidence = round(random.uniform(0.7, 0.95), 2) if severity >= 0.7 else round(random.uniform(0.6, 0.9), 2)

    raw_kb, packed_kb = estimate_sizes(payload)
    ev = StandardEvent(
        event_id=f"evt-{uuid.uuid4().hex[:8]}",
        source=raw.source,
        patient_id=patient_id,
        event_time=now_iso(),
        ingest_time=raw.ingest_time,
        signal=signals,
        severity=round(severity, 2),
        confidence=confidence,
        embedding=fake_embedding(8),
        payload_hint={"raw_size_kb": raw_kb, "packed_size_kb": packed_kb},
        ttl_sec=15 if severity >= 0.7 else 60,
    )
    return ev

class FrontHierMemory:
    """
    ✅ 첨부파일의 '계층형 메모리'를 Back이 아니라 Front에 둔다는 차별점을 시각화하기 위한 모듈
    - Hot: 최근 N개 이벤트
    - Warm: 최근 요약(카운트/평균 severity)
    - Cold: 장기 인덱스(간단 히스토리)
    """
    def __init__(self, hot_max: int = 25):
        self.hot: Deque[StandardEvent] = deque(maxlen=hot_max)
        self.cold_index: Deque[Dict[str, float]] = deque(maxlen=200)

    def push(self, ev: StandardEvent) -> None:
        self.hot.appendleft(ev)
        self.cold_index.appendleft({
            "severity": float(ev.severity),
            "is_emergency": 1.0 if float(ev.severity) >= 0.7 else 0.0,
        })

    def warm_summary(self) -> Dict[str, float]:
        if not self.hot:
            return {"count": 0, "avg_severity": 0.0, "emergency_rate": 0.0}
        vals = [float(e.severity) for e in list(self.hot)]
        emerg = [1.0 for e in list(self.hot) if float(e.severity) >= 0.7]
        return {
            "count": float(len(vals)),
            "avg_severity": round(sum(vals) / len(vals), 2),
            "emergency_rate": round((sum(emerg) / len(vals)) if vals else 0.0, 2),
        }
