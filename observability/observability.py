# observability/observability.py
"""
Data Observability — checks freshness, volume, schema, quality, lineage.
Works for both batch (DataFrame) and stream (list of processed dicts).
"""
import os
import time
from datetime import datetime

import pandas as pd

from utils.logger import get_logger
from utils.file_utils import save_json

logger = get_logger("observability")


# ── Main entry-points ─────────────────────────────────────────────────────────

def run_batch_checks(
    source_file:   str,
    raw_df:        pd.DataFrame,
    valid_df:      pd.DataFrame,
    processed_df:  pd.DataFrame,
    output_file:   str = "batch_processed.csv",
) -> dict:
    """Run all observability checks for the batch pipeline."""
    logger.info("Running batch observability checks …")
    report = _base_report("batch", source_file, output_file)

    # Freshness
    report["freshness"] = _check_freshness(source_file)

    # Volume
    report["volume"] = {
        "source_records":    len(raw_df),
        "valid_records":     len(valid_df),
        "processed_records": len(processed_df),
        "drop_rate_pct":     round(
            (1 - len(valid_df) / max(len(raw_df), 1)) * 100, 2
        ),
    }

    # Schema
    report["schema"] = _check_schema(valid_df)

    # Quality
    report["quality"] = _check_quality(valid_df)

    # Processing
    if "record_latency_sec" in processed_df.columns:
        latencies = processed_df["record_latency_sec"].dropna()
        report["processing"]["avg_latency_sec"] = round(float(latencies.mean()), 4)
        report["processing"]["max_latency_sec"] = round(float(latencies.max()), 4)

    if "processing_source" in processed_df.columns:
        vc = processed_df["processing_source"].value_counts().to_dict()
        report["processing"]["llm_count"]      = vc.get("LLM", 0)
        report["processing"]["fallback_count"] = vc.get("Rule-Based", 0)

    # Lineage
    report["lineage"] = {
        "source_file":    source_file,
        "pipeline_stage": ["ingestion", "validation", "sentiment_analysis", "output"],
        "output_file":    output_file,
        "run_at":         datetime.now().isoformat(),
    }

    _flag_warnings(report)
    save_json(report, "batch_observability_report.json", subdir="processed")
    logger.info("Batch observability checks complete")
    return report


def run_stream_checks(
    source_file:    str,
    total_events:   int,
    processed_list: list,
) -> dict:
    """Run all observability checks for the stream pipeline."""
    logger.info("Running stream observability checks …")
    report = _base_report("stream", source_file, "stream_processed.json")

    # Freshness — use most recent processed_at timestamp
    if processed_list:
        latest = max(r.get("processed_at", "") for r in processed_list)
        report["freshness"]["latest_event_at"] = latest

    # Volume
    report["volume"] = {
        "total_source_events":  total_events,
        "processed_so_far":     len(processed_list),
        "pending":              total_events - len(processed_list),
    }

    # Quality
    df_tmp = pd.DataFrame(processed_list) if processed_list else pd.DataFrame()
    if not df_tmp.empty:
        report["schema"]  = _check_schema(df_tmp)
        report["quality"] = _check_quality(df_tmp)
        if "record_latency_sec" in df_tmp.columns:
            latencies = df_tmp["record_latency_sec"].dropna()
            report["processing"]["avg_latency_sec"] = round(float(latencies.mean()), 4)
        if "processing_source" in df_tmp.columns:
            vc = df_tmp["processing_source"].value_counts().to_dict()
            report["processing"]["llm_count"]      = vc.get("LLM", 0)
            report["processing"]["fallback_count"] = vc.get("Rule-Based", 0)

    # Lineage
    report["lineage"] = {
        "source_file":    source_file,
        "pipeline_stage": ["stream_ingest", "validation", "sentiment_analysis"],
        "output_file":    "stream_processed.json",
        "run_at":         datetime.now().isoformat(),
    }

    _flag_warnings(report)
    save_json(report, "stream_observability_report.json", subdir="processed")
    return report


# ── Internal helpers ──────────────────────────────────────────────────────────

def _base_report(pipeline: str, source_file: str, output_file: str) -> dict:
    return {
        "pipeline":   pipeline,
        "checked_at": datetime.now().isoformat(),
        "source":     source_file,
        "output":     output_file,
        "freshness":  {},
        "volume":     {},
        "schema":     {},
        "quality":    {},
        "processing": {
            "avg_latency_sec": 0.0,
            "max_latency_sec": 0.0,
            "llm_count":       0,
            "fallback_count":  0,
            "errors":          0,
        },
        "lineage":   {},
        "warnings":  [],
        "status":    "OK",
    }


def _check_freshness(file_path: str) -> dict:
    result = {"file_exists": False, "last_modified": None, "age_minutes": None}
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        age   = (time.time() - mtime) / 60
        result.update({
            "file_exists":   True,
            "last_modified": datetime.fromtimestamp(mtime).isoformat(),
            "age_minutes":   round(age, 2),
        })
        if age > 60:
            logger.warning(f"Freshness warning: source file is {age:.1f} minutes old")
    else:
        logger.error(f"Source file not found: {file_path}")
    return result


def _check_schema(df: pd.DataFrame) -> dict:
    required = ["id", "user", "feedback", "timestamp", "source"]
    missing  = [c for c in required if c not in df.columns]
    return {
        "columns_present": list(df.columns),
        "missing_columns": missing,
        "schema_valid":    len(missing) == 0,
    }


def _check_quality(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {"null_feedback": 0, "empty_rows": 0, "duplicates": 0, "quality_score": 0}

    null_fb  = int(df["feedback"].isna().sum()) if "feedback" in df else 0
    empty    = int(df.isnull().all(axis=1).sum())
    dups     = int(df.duplicated(subset=["id"]).sum()) if "id" in df else 0
    score    = round((1 - (null_fb + empty + dups) / max(total, 1)) * 100, 1)

    return {
        "null_feedback": null_fb,
        "empty_rows":    empty,
        "duplicates":    dups,
        "quality_score": score,
    }


def _flag_warnings(report: dict):
    warns = []
    if not report.get("schema", {}).get("schema_valid", True):
        warns.append("Schema validation failed — missing columns detected")
    if report.get("quality", {}).get("null_feedback", 0) > 0:
        warns.append("Null feedback values detected in records")
    if report.get("quality", {}).get("duplicates", 0) > 0:
        warns.append("Duplicate records detected")
    if report.get("volume", {}).get("drop_rate_pct", 0) > 20:
        warns.append("High record drop rate (>20%) during validation")

    report["warnings"] = warns
    report["status"]   = "WARN" if warns else "OK"
    if warns:
        for w in warns:
            logger.warning(f"Observability: {w}")
