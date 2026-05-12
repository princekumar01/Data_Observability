# dashboard/batch_dashboard.py
"""
Batch Pipeline Dashboard — run with:
    streamlit run dashboard/batch_dashboard.py
"""
import os
import sys
import json
from datetime import datetime

import pandas as pd
import streamlit as st

# Allow imports from project root
ROOT = os.path.join(os.path.dirname(__file__), "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ingestion.batch_ingestor import ingest_batch
from validation.validator import validate_batch
from processing.sentiment_processor import process_batch
from observability.observability import run_batch_checks

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Batch Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
)

CSV_PATH = os.path.join(ROOT, "data", "feedback.csv")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Batch Pipeline Dashboard")
st.caption("Customer Feedback — CSV Batch Processing")
st.divider()

# ── Trigger ───────────────────────────────────────────────────────────────────
col_btn, col_ts = st.columns([2, 3])
with col_btn:
    run_batch = st.button("▶  Run Batch Processing", type="primary", use_container_width=True)
with col_ts:
    ts_placeholder = st.empty()

if run_batch:
    with st.status("Running batch pipeline …", expanded=True) as status:

        # 1. Ingest
        st.write("📥 Ingesting CSV …")
        ingest = ingest_batch(CSV_PATH)
        if not ingest["success"]:
            st.error(f"Ingestion failed: {ingest['error']}")
            st.stop()

        # 2. Validate
        st.write("✅ Validating records …")
        val = validate_batch(ingest["dataframe"])

        # 3. Process
        st.write("🤖 Running sentiment analysis …")
        proc = process_batch(val["valid_df"])

        # 4. Observability
        st.write("🔍 Running observability checks …")
        obs = run_batch_checks(
            source_file=CSV_PATH,
            raw_df=ingest["dataframe"],
            valid_df=val["valid_df"],
            processed_df=proc["processed_df"],
        )

        status.update(label="✅ Batch pipeline complete!", state="complete")

    # Store in session for display
    st.session_state["batch_ingest"]   = ingest
    st.session_state["batch_val"]      = val
    st.session_state["batch_proc"]     = proc
    st.session_state["batch_obs"]      = obs
    st.session_state["batch_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Display results ───────────────────────────────────────────────────────────
if "batch_proc" not in st.session_state:
    st.info("👆 Click **Run Batch Processing** to start.")
    st.stop()

ingest  = st.session_state["batch_ingest"]
val     = st.session_state["batch_val"]
proc    = st.session_state["batch_proc"]
obs     = st.session_state["batch_obs"]
run_ts  = st.session_state["batch_run_time"]

ts_placeholder.success(f"Last run: {run_ts}")

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.subheader("📈 Summary Metrics")
k1, k2, k3, k4, k5 = st.columns(5)
sc = proc["metrics"]["sentiment_counts"]
k1.metric("Total Records",   ingest["record_count"])
k2.metric("Positive 😊",      sc.get("Positive", 0))
k3.metric("Negative 😞",      sc.get("Negative", 0))
k4.metric("Neutral 😐",       sc.get("Neutral",  0))
k5.metric("Failed / Invalid", val["report"]["invalid_count"])

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_chart, col_src = st.columns(2)

with col_chart:
    st.subheader("🥧 Sentiment Distribution")
    sentiment_data = pd.DataFrame(
        list(sc.items()), columns=["Sentiment", "Count"]
    ).set_index("Sentiment")
    st.bar_chart(sentiment_data, color="#5B8FF9")

with col_src:
    st.subheader("🤖 Processing Source")
    df_proc = proc["processed_df"]
    src_vc  = df_proc["processing_source"].value_counts()
    src_df  = pd.DataFrame({"Count": src_vc}).reset_index()
    src_df.columns = ["Source", "Count"]
    st.bar_chart(src_df.set_index("Source"), color="#61D9A4")

st.divider()

# ── Processed records table ───────────────────────────────────────────────────
st.subheader("📋 Processed Records")
display_cols = ["id", "user", "feedback", "sentiment", "processing_source",
                "processed_at", "record_latency_sec"]
show_cols    = [c for c in display_cols if c in df_proc.columns]

def _color_sentiment(val):
    colors = {"Positive": "background-color:#d4edda;color:#155724",
              "Negative": "background-color:#f8d7da;color:#721c24",
              "Neutral":  "background-color:#fff3cd;color:#856404"}
    return colors.get(val, "")

styled = df_proc[show_cols].style.map(_color_sentiment, subset=["sentiment"])
st.dataframe(styled, use_container_width=True)

st.divider()

# ── Validation report ─────────────────────────────────────────────────────────
st.subheader("✅ Validation Report")
report = val["report"]
vc1, vc2, vc3, vc4 = st.columns(4)
vc1.metric("Valid",      report["valid_count"])
vc2.metric("Invalid",    report["invalid_count"])
vc3.metric("Duplicates", report["duplicate_count"])
vc4.metric("Latency",    f"{report['latency_sec']}s")

if report["issues"]:
    for issue in report["issues"]:
        st.warning(f"⚠️  {issue}")
else:
    st.success("No validation issues found")

if not val["invalid_df"].empty:
    with st.expander("View Invalid Records"):
        st.dataframe(val["invalid_df"], use_container_width=True)

st.divider()

# ── Observability ─────────────────────────────────────────────────────────────
st.subheader("🔍 Observability Status")
status_badge = "🟢 OK" if obs["status"] == "OK" else "🟡 WARN"
st.markdown(f"**Overall Status:** {status_badge}")

oc1, oc2, oc3 = st.columns(3)
with oc1:
    st.markdown("**Freshness**")
    st.json(obs.get("freshness", {}))
with oc2:
    st.markdown("**Volume**")
    st.json(obs.get("volume", {}))
with oc3:
    st.markdown("**Quality**")
    st.json(obs.get("quality", {}))

if obs.get("warnings"):
    for w in obs["warnings"]:
        st.warning(f"⚠️  {w}")

with st.expander("📦 Lineage"):
    st.json(obs.get("lineage", {}))

with st.expander("⚙️ Processing Metrics"):
    m = proc["metrics"]
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("LLM Calls",    m["llm_count"])
    pc2.metric("Fallback",     m["fallback_count"])
    pc3.metric("Total Latency",f"{m['total_latency']}s")
