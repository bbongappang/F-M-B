from __future__ import annotations
import streamlit as st
import pandas as pd

from .generators import gen_nurse_note, gen_wearable_spike, gen_ambulance_app, gen_network_degradation
from .front import normalize, FrontHierMemory
from .middle import make_intent, ml_generate_constraints
from .optimizer import decide
from .api_sim import apply_network, apply_ris, apply_ai_ran
from .back import execute
from .metrics import koi_from, effect_mapping

def init_session_state():
    if "raw_inbox" not in st.session_state:
        st.session_state.raw_inbox = []
    if "events" not in st.session_state:
        st.session_state.events = []
    if "front_mem" not in st.session_state:
        st.session_state.front_mem = FrontHierMemory(hot_max=25)
    if "latest" not in st.session_state:
        st.session_state.latest = {
            "phase": "Normal",
            "active_slice": "eMBB",
            "ris": "OFF",
            "ai_ran": "Baseline",
            "koi": {"mission_success": 0, "operational_cost": 0, "stability": 0},
        }
    if "api_calls" not in st.session_state:
        st.session_state.api_calls = []
    if "history" not in st.session_state:
        st.session_state.history = []  # telemetry + koi history
    if "effect_cards" not in st.session_state:
        st.session_state.effect_cards = []

def render_top_status_bar():
    latest = st.session_state.latest
    c1, c2, c3, c4, c5 = st.columns([1.1, 1, 1, 1, 1.8])
    with c1:
        st.metric("Phase", latest["phase"])
    with c2:
        st.metric("Active Slice", latest["active_slice"])
    with c3:
        st.metric("Selective RIS", latest["ris"])
    with c4:
        st.metric("AI-RAN", latest["ai_ran"])
    with c5:
        koi = latest["koi"]
        st.metric("KOI (Mission/Cost/Stability)", f'{koi["mission_success"]} / {koi["operational_cost"]} / {koi["stability"]}')

def _push_raw_and_process(raw):
    st.session_state.raw_inbox.insert(0, raw)

    ev = normalize(raw)
    st.session_state.events.insert(0, ev)
    st.session_state.front_mem.push(ev)

    intent = make_intent(ev)
    constraints = ml_generate_constraints(ev)
    decision = decide(intent, constraints)

    # "API 호출" 연출
    calls = []
    calls.append(apply_network({"slice_id": decision.slice_id, "latency_budget_ms": constraints.latency_budget_ms, "reliability": constraints.reliability_target}))
    calls.append(apply_ris({"active": decision.ris_active, "zone": decision.ris_zone}))
    calls.append(apply_ai_ran({"mode": decision.ai_ran_mode, "penalty_weights": constraints.penalty_weights}))
    st.session_state.api_calls = calls

    # Back 실행 & telemetry
    tele = execute(decision)

    # KOI 점수
    koi = koi_from(tele, decision, constraints, intent)
    st.session_state.latest["koi"] = koi.to_dict()
    st.session_state.latest["active_slice"] = decision.slice_id
    st.session_state.latest["ris"] = decision.ris_zone if decision.ris_active else "OFF"
    st.session_state.latest["ai_ran"] = decision.ai_ran_mode

    # Phase
    if intent.context == "EMERGENCY_CRITICAL":
        st.session_state.latest["phase"] = "Emergency"
    elif intent.context == "EMERGENCY_SUSPECT":
        st.session_state.latest["phase"] = "Alert"
    else:
        st.session_state.latest["phase"] = "Normal"

    # 기록(Results 탭)
    st.session_state.history.insert(0, {
        "latency_ms": tele.latency_ms,
        "loss_pct": tele.loss_pct,
        "jitter_ms": tele.jitter_ms,
        "coverage_ok": tele.coverage_ok,
        "koi_mission": koi.mission_success,
        "koi_cost": koi.operational_cost,
        "koi_stability": koi.stability,
        "slice": decision.slice_id,
        "ris_active": decision.ris_active,
        "ai_ran": decision.ai_ran_mode,
        "uncertainty": constraints.uncertainty,
        "lat_budget": constraints.latency_budget_ms,
    })

    st.session_state.effect_cards = effect_mapping(decision)

    return raw, ev, intent, constraints, decision, tele, koi

def tab_live_intake():
    st.subheader("Live Intake (Free-form Input → Front Normalize/Embed → Event Bus)")

    b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 2])
    with b1:
        if st.button("Generate Nurse Note 🧾"):
            _push_raw_and_process(gen_nurse_note("A"))
    with b2:
        if st.button("Generate Wearable Spike 📟"):
            _push_raw_and_process(gen_wearable_spike("A"))
    with b3:
        if st.button("Generate Ambulance App 📱"):
            _push_raw_and_process(gen_ambulance_app("A"))
    with b4:
        if st.button("Generate Network Degradation 📡"):
            _push_raw_and_process(gen_network_degradation("A"))
    with b5:
        st.info("✅ 차별점: **계층형 메모리를 Back이 아니라 Front에 배치** (real-time triage & retrieval)")

    colL, colM, colR = st.columns([1.2, 1.2, 1.4])

    # (좌) Raw Inbox
    with colL:
        st.markdown("### (Left) Raw Inbox")
        for raw in st.session_state.raw_inbox[:6]:
            st.markdown(f"**{raw.source}**  ·  `{raw.raw_id}`")
            st.code(str(raw.payload), language="json")
            st.caption(f"ingest_time: {raw.ingest_time}")
            st.divider()

    # (중) Normalizer / Embedding
    with colM:
        st.markdown("### (Middle) Normalizer / Embedding")
        if st.session_state.events:
            ev = st.session_state.events[0]
            st.write("**Standard Event(JSON)**")
            st.json(ev.to_dict())
            st.write("**Embedding (dim=8)**")
            st.code(str(ev.embedding))
            st.write("**Payload Compression**")
            st.metric("raw_size_kb → packed_size_kb", f'{ev.payload_hint["raw_size_kb"]} → {ev.payload_hint["packed_size_kb"]}')
        else:
            st.warning("왼쪽 버튼으로 자유형 데이터를 생성해보세요.")

    # (우) Event Bus
    with colR:
        st.markdown("### (Right) Event Bus (Front Output)")
        for ev in st.session_state.events[:6]:
            st.markdown(f"**{ev.source}** · `{ev.event_id}` · patient={ev.patient_id}")
            st.caption(f"signal={ev.signal} | severity={ev.severity} | ttl={ev.ttl_sec}s")
            st.divider()

    # Front Hierarchical Memory (하단)
    st.markdown("### Front Hierarchical Memory (Hot / Warm / Cold)")
    c1, c2, c3 = st.columns([1, 1, 1.3])
    with c1:
        st.write("**Hot Memory (recent)**")
        hot = [e.to_dict() for e in list(st.session_state.front_mem.hot)[:5]]
        if hot:
            st.json(hot)
        else:
            st.caption("No events yet.")
    with c2:
        st.write("**Warm Summary**")
        st.json(st.session_state.front_mem.warm_summary())
    with c3:
        st.write("**Cold Index (longer-term pointers)**")
        cold = list(st.session_state.front_mem.cold_index)[:10]
        if cold:
            st.dataframe(pd.DataFrame(cold))
        else:
            st.caption("No index yet.")

def tab_pipeline_view():
    st.subheader("F–M–B Pipeline View (Front → Middle → Optimizer → Back)")

    st.markdown(
        """
**핵심 원칙**
- ML/LLM은 **결정을 내리지 않음**
- ML은 **제약(임계/상하한/벌점 가중치/불확실성)**을 생성/갱신
- 최종 결정은 **규칙/최적화(Optimizer)**가 수행
        """
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        st.markdown("### Front")
        st.success("Intake → Normalize → Embed → **Front Memory** → Event")
        st.caption("Free-form → Standard Event(JSON)")
    with col2:
        st.markdown("### Middle")
        st.warning("Context → Policy Map → **Constraints(ML)** → Intent")
        st.caption("ML outputs constraints, not decisions")
    with col3:
        st.markdown("### Optimizer (Decision)")
        st.info("Rule + Optimization → Slice/RIS/AI-RAN config")
        st.caption("Decision maker")
    with col4:
        st.markdown("### Back")
        st.success("Selective RIS + AI-RAN Apply → Telemetry")
        st.caption("Execution & feedback")

    st.divider()

    if st.session_state.events:
        ev = st.session_state.events[0]
        from .middle import make_intent, ml_generate_constraints
        from .optimizer import decide
        intent = make_intent(ev)
        c = ml_generate_constraints(ev)
        d = decide(intent, c)

        a, b, ccol = st.columns([1.2, 1.2, 1.2])
        with a:
            st.markdown("#### Latest Event")
            st.json(ev.to_dict())
        with b:
            st.markdown("#### Middle Output (Intent + Constraints)")
            st.json({"intent": intent.to_dict(), "constraints": c.to_dict()})
        with ccol:
            st.markdown("#### Optimizer Decision")
            st.json(d.to_dict())
    else:
        st.warning("Live Intake에서 데이터를 먼저 생성하세요.")

def tab_api_console():
    st.subheader("API Console (Intent/Decision → API Calls → Applied)")

    if st.session_state.api_calls:
        left, right = st.columns([1.2, 1.2])
        with left:
            st.markdown("### Decision Payload (applied by Optimizer)")
            if st.session_state.history:
                last = st.session_state.history[0]
                st.json({
                    "slice": last["slice"],
                    "latency_budget_ms": last["lat_budget"],
                    "uncertainty": last["uncertainty"],
                    "ai_ran": last["ai_ran"],
                    "ris_active": last["ris_active"],
                })
        with right:
            st.markdown("### API Calls")
            for call in st.session_state.api_calls:
                st.code(f'{call.method} {call.path}')
                st.write("body:")
                st.json(call.body)
                st.write("response:")
                st.json(call.response)
                st.divider()
    else:
        st.info("아직 API 호출이 없습니다. Live Intake에서 이벤트를 생성하면 자동으로 호출됩니다.")

def tab_results_effects():
    st.subheader("Results & Effect Mapping (KPI → KOI)")

    if not st.session_state.history:
        st.warning("아직 결과가 없습니다. Live Intake에서 이벤트를 생성하세요.")
        return

    df = pd.DataFrame(st.session_state.history[:30])

    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.markdown("### Telemetry (KPI-like)")
        st.dataframe(df[["latency_ms", "loss_pct", "jitter_ms", "coverage_ok", "slice", "ai_ran", "ris_active"]])

    with c2:
        st.markdown("### KOI Score (Goal-based)")
        last = st.session_state.history[0]
        st.metric("Mission Success (0-100)", last["koi_mission"])
        st.metric("Operational Cost (0-100, higher=better)", last["koi_cost"])
        st.metric("Stability (0-100)", last["koi_stability"])

    st.divider()

    st.markdown("### Before / After 느낌의 추세(최근 10회)")
    recent = df.head(10).iloc[::-1]  # 오래된→최신
    st.line_chart(recent[["latency_ms", "loss_pct", "jitter_ms"]], height=220)
    st.line_chart(recent[["koi_mission", "koi_cost", "koi_stability"]], height=220)

    st.divider()

    st.markdown("### Effect Mapping (원인 → 개선효과)")
    cards = st.session_state.effect_cards or []
    cols = st.columns(3)
    for i, card in enumerate(cards[:3]):
        with cols[i]:
            st.markdown(f"**Cause**: {card['cause']}")
            st.markdown(f"**Effect**: {card['effect']}")
            st.caption("‘성능’이 아니라 ‘개입 시점/운영 카드’로 설명")

    st.divider()
    st.markdown("### 발표 멘트 한 줄(자동)")
    st.success("“우리는 KPI를 올리는 게 아니라, 응급 상황에서 **목표 달성(KOI)**을 보장하기 위해 통신이 **언제·어떻게 개입할지**를 운영합니다.”")
