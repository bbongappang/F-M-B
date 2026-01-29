import streamlit as st

from src.ui import (
    init_session_state,
    render_top_status_bar,
    tab_live_intake,
    tab_pipeline_view,
    tab_api_console,
    tab_results_effects,
)

st.set_page_config(
    page_title="F–M–B Medical Communication Ops Demo",
    page_icon="🩺",
    layout="wide",
)

def main():
    init_session_state()

    st.title("🩺 F–M–B Medical Communication Operation Console")
    st.caption("Free-form Data → Front(Memory) → Middle(Constraints) → Optimizer(Decision) → API → Back(Selective RIS/AI-RAN) → KOI & Effect Mapping")

    render_top_status_bar()

    tabs = st.tabs(["1) Live Intake", "2) F–M–B Pipeline", "3) API Console", "4) Results & Effect Mapping"])
    with tabs[0]:
        tab_live_intake()
    with tabs[1]:
        tab_pipeline_view()
    with tabs[2]:
        tab_api_console()
    with tabs[3]:
        tab_results_effects()

if __name__ == "__main__":
    main()
