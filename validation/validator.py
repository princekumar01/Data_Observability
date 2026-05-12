# validation/validator.py
"""
Validation layer — used by BOTH the batch and stream pipelines.

For batch: pass a DataFrame.
For stream: pass a single record dict (wrapped as a one-row DataFrame internally).
"""
import time
from datetime import datetime
import pandas as pd
from utils.logger import get_logger
from utils.file_utils import save_csv, save_json

logger = get_logger("validator")

REQUIRED_COLUMNS = ["id", "user", "feedback", "timestamp", "source"]


# ── Main entry-points ─────────────────────────────────────────────────────────

def validate_batch(df: pd.DataFrame, seen_ids: set | None = None) -> dict:
    """Validate all records in the DataFrame and return a validation report."""
    start = time.time()
    logger.info(f"Validation started — {len(df)} records")

    report = _build_empty_report()
    report["total_input"] = len(df)
    report["pipeline"]    = "batch"

    # 1. Schema check
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    report["schema_errors"] = missing_cols
    if missing_cols:
        logger.warning(f"Schema validation — missing columns: {missing_cols}")

    valid_mask = pd.Series([True] * len(df), index=df.index)

    # 2. Null / empty feedback
    null_fb = df["feedback"].isna() | (df["feedback"].astype(str).str.strip() == "")
    if null_fb.any():
        count = null_fb.sum()
        report["null_feedback_count"] = int(count)
        report["issues"].append(f"{count} record(s) have empty/null feedback")
        logger.warning(f"Null feedback detected in {count} record(s)")
        valid_mask &= ~null_fb

    # 3. Null timestamp
    null_ts = df["timestamp"].isna()
    if null_ts.any():
        count = null_ts.sum()
        report["null_timestamp_count"] = int(count)
        report["issues"].append(f"{count} record(s) have null timestamp")
        logger.warning(f"Null timestamp detected in {count} record(s)")
        valid_mask &= ~null_ts

    # 4. Duplicate id detection
    dup_mask = df.duplicated(subset=["id"], keep="first")
    if seen_ids:
        cross_dup = df["id"].isin(seen_ids)
        dup_mask  = dup_mask | cross_dup
    if dup_mask.any():
        count = dup_mask.sum()
        report["duplicate_count"] = int(count)
        report["issues"].append(f"{count} duplicate record(s) found")
        logger.warning(f"Duplicate records: {count}")
        valid_mask &= ~dup_mask

    # 5. Type validation — id must be numeric
    non_numeric = pd.to_numeric(df["id"], errors="coerce").isna()
    if non_numeric.any():
        count = non_numeric.sum()
        report["type_errors"] = int(count)
        report["issues"].append(f"{count} record(s) have non-numeric id")
        logger.warning(f"Non-numeric id in {count} record(s)")
        valid_mask &= ~non_numeric

    # Split valid / invalid
    valid_df   = df[valid_mask].copy()
    invalid_df = df[~valid_mask].copy()

    report["valid_count"]   = len(valid_df)
    report["invalid_count"] = len(invalid_df)
    report["latency_sec"]   = round(time.time() - start, 4)
    report["validated_at"]  = datetime.now().isoformat()

    # Persist outputs
    _save_validation_outputs(valid_df, invalid_df, report, prefix="batch")

    logger.info(f"Validation complete — valid: {len(valid_df)}, "
                f"invalid: {len(invalid_df)}, took {report['latency_sec']}s")
    return {
        "valid_df":   valid_df,
        "invalid_df": invalid_df,
        "report":     report,
    }


def validate_record(record: dict, seen_ids: set | None = None) -> dict:
    """Validate a single stream record.  Returns same structure as validate_batch."""
    df     = pd.DataFrame([record])
    result = validate_batch(df, seen_ids=seen_ids)
    # Return first (and only) valid/invalid row as dict for convenience
    result["is_valid"] = len(result["valid_df"]) == 1
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_empty_report() -> dict:
    return {
        "pipeline":            "unknown",
        "total_input":         0,
        "valid_count":         0,
        "invalid_count":       0,
        "schema_errors":       [],
        "null_feedback_count": 0,
        "null_timestamp_count":0,
        "duplicate_count":     0,
        "type_errors":         0,
        "issues":              [],
        "latency_sec":         0.0,
        "validated_at":        "",
    }


def _save_validation_outputs(valid_df, invalid_df, report, prefix="batch"):
    save_csv(valid_df,   f"{prefix}_valid_records.csv",   subdir="validation")
    save_csv(invalid_df, f"{prefix}_invalid_records.csv", subdir="validation")
    save_json(report,    f"{prefix}_validation_report.json", subdir="validation")
