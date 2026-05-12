# main.py
"""
CLI entry-point — runs the BATCH pipeline end-to-end from the terminal.

Usage:
    python main.py

The two dashboards are launched separately:
    streamlit run dashboard/batch_dashboard.py
    streamlit run dashboard/stream_dashboard.py
"""
import os
import sys

ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ingestion.batch_ingestor import ingest_batch
from validation.validator import validate_batch
from processing.sentiment_processor import process_batch
from observability.observability import run_batch_checks
from utils.logger import get_logger

logger = get_logger("main")

CSV_PATH = os.path.join(ROOT, "data", "feedback.csv")


def run_batch_pipeline():
    logger.info("=" * 60)
    logger.info("BATCH PIPELINE START")
    logger.info("=" * 60)

    # ── 1. Ingestion ─────────────────────────────────────────────
    logger.info("Step 1/4 — Ingestion")
    ingest = ingest_batch(CSV_PATH)
    if not ingest["success"]:
        logger.error(f"Ingestion failed: {ingest['error']}")
        return

    print(f"\n✅ Ingested {ingest['record_count']} records from {CSV_PATH}")

    # ── 2. Validation ────────────────────────────────────────────
    logger.info("Step 2/4 — Validation")
    val = validate_batch(ingest["dataframe"])
    print(f"✅ Validation: {val['report']['valid_count']} valid, "
          f"{val['report']['invalid_count']} invalid")

    # ── 3. Sentiment Analysis ────────────────────────────────────
    logger.info("Step 3/4 — Sentiment Analysis")
    proc = process_batch(val["valid_df"])
    sc   = proc["metrics"]["sentiment_counts"]
    print(f"✅ Sentiment: Positive={sc.get('Positive',0)} "
          f"Negative={sc.get('Negative',0)} Neutral={sc.get('Neutral',0)}")
    print(f"   LLM={proc['metrics']['llm_count']} "
          f"Fallback={proc['metrics']['fallback_count']}")

    # ── 4. Observability ─────────────────────────────────────────
    logger.info("Step 4/4 — Observability")
    obs = run_batch_checks(
        source_file=CSV_PATH,
        raw_df=ingest["dataframe"],
        valid_df=val["valid_df"],
        processed_df=proc["processed_df"],
    )
    print(f"✅ Observability: status={obs['status']}  "
          f"quality_score={obs['quality'].get('quality_score','?')}")

    if obs["warnings"]:
        for w in obs["warnings"]:
            print(f"   ⚠️  {w}")

    logger.info("BATCH PIPELINE COMPLETE")
    print("\n📂 Outputs written to output/processed/ and output/validation/")
    print("📄 Logs written to logs/app.log")
    print("\nTo view dashboards:")
    print("  streamlit run dashboard/batch_dashboard.py")
    print("  streamlit run dashboard/stream_dashboard.py")


if __name__ == "__main__":
    run_batch_pipeline()
