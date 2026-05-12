# stream/stream_simulator.py
"""
Stream simulator — manages state for the Streamlit stream dashboard.

We store state in a flat JSON file so Streamlit reruns can pick it up.
"""
import json
import os
import time
from datetime import datetime

from ingestion.stream_ingestor import ingest_stream
from validation.validator import validate_record
from processing.sentiment_processor import process_record
from observability.observability import run_stream_checks
from utils.file_utils import save_json
from utils.logger import get_logger

logger = get_logger("stream_simulator")

STATE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "output", "processed", "stream_state.json"
)


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "processed": [],
        "current_index": 0,
        "started_at": None,
        "last_event_at": None,
        "source_file": None,
        "total_source": 0,
        "obs_report": {},
    }


def _save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, default=str)


def reset_stream():
    """Clear stream state so the simulation starts fresh."""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    logger.info("Stream state reset")


def tick(json_path: str) -> dict:
    """
    Called by the Streamlit dashboard every 5 seconds (via rerun).
    Processes the NEXT unprocessed record and updates state.

    Returns current state dict.
    """
    state = _load_state()

    # First tick — initialise
    if state["started_at"] is None:
        ingest = ingest_stream(json_path)
        if not ingest["success"]:
            logger.error(f"Stream ingestion failed: {ingest['error']}")
            return state
        # Cache the raw records list inside state for subsequent ticks
        state["all_records"]   = ingest["records"]
        state["total_source"]  = ingest["total"]
        state["source_file"]   = json_path
        state["started_at"]    = datetime.now().isoformat()
        state["current_index"] = 0
        logger.info(f"Stream simulation initialised — {ingest['total']} events")

    all_records = state.get("all_records", [])
    idx         = state["current_index"]

    if idx >= len(all_records):
        logger.info("Stream simulation complete — all records processed")
        _save_state(state)
        return state  # Nothing left to process

    record = all_records[idx]
    logger.info(f"Stream event {idx+1}/{len(all_records)} — id={record.get('id')}")

    # Validate
    seen_ids = {r["id"] for r in state["processed"]}
    val_result = validate_record(record, seen_ids=seen_ids)

    if val_result["is_valid"]:
        enriched = process_record(record)
    else:
        enriched = {
            **record,
            "sentiment":         "Invalid",
            "processing_source": "Skipped",
            "processed_at":      datetime.now().isoformat(),
            "record_latency_sec": 0.0,
            "validation_error":  str(val_result["report"]["issues"]),
        }
        logger.warning(f"Stream record id={record.get('id')} failed validation — skipped")

    state["processed"].append(enriched)
    state["current_index"]  = idx + 1
    state["last_event_at"]  = datetime.now().isoformat()

    # Observability on every tick
    obs = run_stream_checks(
        source_file=state["source_file"],
        total_events=state["total_source"],
        processed_list=state["processed"],
    )
    state["obs_report"] = obs

    # Persist processed list as JSON output
    save_json(state["processed"], "stream_processed.json", subdir="processed")

    _save_state(state)
    return state


def get_state() -> dict:
    return _load_state()
