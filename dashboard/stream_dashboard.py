# dashboard/stream_dashboard.py
"""
Stream Pipeline Dashboard — run with:
    streamlit run dashboard/stream_dashboard.py
"""
import os
import sys
import time
from datetime import datetime

import pandas as pd
import streamlit as st

ROOT = os.path.join(os.path.dirname(__file__), "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stream.stream_simulator import tick, reset_stream, get_state

JSON_PATH = os.path.join(ROOT, "data", "stream_feedback.json")
INTERVAL  = 5  # seconds between stream ticks

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stream Pipeline Dashboard",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Stream Pipeline Dashboard")
st.caption("Customer Feedback — Real-Time Stream Simulation (1 event every 5 seconds)")
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 3])
with ctrl1:
    start_btn = st.button("▶  Start Stream", type="primary", use_container_width=True)
with ctrl2:
    reset_btn = st.button("🔄  Reset Stream", use_container_width=True)
with ctrl3:
    live_placeholder = st.empty()

# Session flags
if "stream_running" not in st.session_state:
    st.session_state["stream_running"]  = False
if "last_tick" not in st.session_state:
    st.session_state["last_tick"] = 0.0

if reset_btn:
    reset_stream()
    st.session_state["stream_running"]  = False
    st.session_state["last_tick"] = 0.0
    st.success("Stream reset — click Start to begin again")
    st.stop()

if start_btn:
    st.session_state["stream_running"] = True

# ── Auto-refresh loop ─────────────────────────────────────────────────────────
if st.session_state["stream_running"]:
    now  = time.time()
    last = st.session_state["last_tick"]

    if now - last >= INTERVAL:
        state = tick(JSON_PATH)
        st.session_state["last_tick"] = now

        if state["current_index"] >= state.get("total_source", 0) > 0:
            st.session_state["stream_running"] = False
            live_placeholder.success("✅ Stream simulation complete!")
        else:
            live_placeholder.info(
                f"⏱ Live — {state['current_index']}/{state.get('total_source',0)} "
                f"events processed"
            )
    else:
        wait = INTERVAL - (now - last)
        live_placeholder.info(f"⏳ Next event in {wait:.1f}s …")


# ── Load current state ────────────────────────────────────────────────────────
state = get_state()
processed = state.get("processed", [])

if not processed:
    st.info("👆 Click **Start Stream** to begin the live simulation.")
    st.stop()

df = pd.DataFrame(processed)

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.subheader("📈 Live Metrics")
total = state.get("total_source", len(processed))
sc    = df["sentiment"].value_counts() if "sentiment" in df else {}

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Processed",    len(processed))
k2.metric("Total Events", total)
k3.metric("Positive 😊",  int(sc.get("Positive", 0)))
k4.metric("Negative 😞",  int(sc.get("Negative", 0)))
k5.metric("Neutral 😐",   int(sc.get("Neutral",  0)))

st.divider()

# ── Live sentiment chart ──────────────────────────────────────────────────────
col_chart, col_src = st.columns(2)

with col_chart:
    st.subheader("📊 Sentiment So Far")
    if "sentiment" in df:
        sd = df["sentiment"].value_counts().reset_index()
        sd.columns = ["Sentiment", "Count"]
        st.bar_chart(sd.set_index("Sentiment"), color="#5B8FF9")

with col_src:
    st.subheader("⏱ Latency Per Record (sec)")
    if "record_latency_sec" in df:
        lat_df = df[["id", "record_latency_sec"]].copy()
        lat_df["id"] = lat_df["id"].astype(str)
        st.line_chart(lat_df.set_index("id"), color="#F4A460")

st.divider()

# ── Live records table ────────────────────────────────────────────────────────
st.subheader("📋 Streamed Records (Latest First)")
display_cols = ["id", "user", "feedback", "sentiment", "processing_source",
                "processed_at", "record_latency_sec"]
show_cols = [c for c in display_cols if c in df.columns]

def _color_sentiment(val):
    colors = {"Positive": "background-color:#d4edda;color:#155724",
              "Negative": "background-color:#f8d7da;color:#721c24",
              "Neutral":  "background-color:#fff3cd;color:#856404",
              "Invalid":  "background-color:#e2e3e5;color:#383d41"}
    return colors.get(val, "")

styled = (
    df[show_cols]
    .sort_values("processed_at", ascending=False)
    .style.map(_color_sentiment, subset=["sentiment"])
)
st.dataframe(styled, use_container_width=True)

st.divider()

# ── Observability ─────────────────────────────────────────────────────────────
obs = state.get("obs_report", {})
if obs:
    st.subheader("🔍 Observability Status")
    status_badge = "🟢 OK" if obs.get("status") == "OK" else "🟡 WARN"
    st.markdown(f"**Overall Status:** {status_badge}")

    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        st.markdown("**Volume**")
        st.json(obs.get("volume", {}))
    with oc2:
        st.markdown("**Quality**")
        st.json(obs.get("quality", {}))
    with oc3:
        st.markdown("**Processing**")
        st.json(obs.get("processing", {}))

    if obs.get("warnings"):
        for w in obs["warnings"]:
            st.warning(f"⚠️  {w}")

# ── Timestamps ────────────────────────────────────────────────────────────────
if state.get("started_at"):
    st.caption(f"🟢 Stream started: {state['started_at']}   |   "
               f"Last event: {state.get('last_event_at','—')}")

# Schedule the next refresh only after the latest state has rendered.
if st.session_state["stream_running"]:
    time.sleep(1)
    st.rerun()
