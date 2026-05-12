# processing/sentiment_processor.py
"""
AI Processing Layer — two-level sentiment analysis.

Level 1 (Primary)  : LLM via llm_config.py
Level 2 (Fallback) : Rule-based keyword classifier
"""
import time
from datetime import datetime

import pandas as pd

from llm_config import llm, LLM_MODEL
from processing.rule_based import classify as rule_classify
from utils.logger import get_logger
from utils.file_utils import save_csv, save_json

logger = get_logger("sentiment_processor")

SENTIMENT_PROMPT = """You are a sentiment analysis engine.

Analyze the customer feedback below and respond with EXACTLY one of:
  Positive
  Negative
  Neutral

Feedback: "{feedback}"

Reply with only the single sentiment word — nothing else."""


# ── LLM call ─────────────────────────────────────────────────────────────────

def _llm_sentiment(feedback: str) -> tuple[str, str]:
    """
    Call the LLM and return (sentiment, source).
    source is "LLM" on success, "Rule-Based" on fallback.
    """
    try:
        resp = llm.invoke(SENTIMENT_PROMPT.format(feedback=feedback))
        raw = resp.content.strip()
        # Normalise to one of three labels
        if "positive" in raw.lower():
            sentiment = "Positive"
        elif "negative" in raw.lower():
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        logger.debug(f"LLM -> '{feedback[:60]}' : {sentiment}")
        return sentiment, "LLM"

    except Exception as e:
        logger.warning(f"LLM failed ({type(e).__name__}: {e}) — activating fallback")
        sentiment = rule_classify(feedback)
        logger.info(f"Fallback -> '{feedback[:60]}' : {sentiment}")
        return sentiment, "Rule-Based"


# ── Public functions ──────────────────────────────────────────────────────────

def process_batch(valid_df: pd.DataFrame) -> dict:
    """
    Run sentiment analysis on every row and return enriched DataFrame + metrics.
    """
    logger.info(f"Batch processing started — {len(valid_df)} records")
    start = time.time()

    results = []
    llm_count      = 0
    fallback_count = 0
    errors         = 0

    for _, row in valid_df.iterrows():
        rec_start = time.time()
        feedback  = str(row.get("feedback", ""))

        try:
            sentiment, source = _llm_sentiment(feedback)
        except Exception as e:
            logger.error(f"Unexpected error for record {row.get('id')}: {e}")
            sentiment, source = rule_classify(feedback), "Rule-Based"
            errors += 1

        if source == "LLM":
            llm_count += 1
        else:
            fallback_count += 1

        results.append({
            **row.to_dict(),
            "sentiment":          sentiment,
            "processing_source":  source,
            "processed_at":       datetime.now().isoformat(),
            "record_latency_sec": round(time.time() - rec_start, 4),
        })

    processed_df = pd.DataFrame(results)
    total_latency = round(time.time() - start, 4)

    # Save output
    save_csv(processed_df, "batch_processed.csv", subdir="processed")

    metrics = {
        "total_records":   len(valid_df),
        "llm_count":       llm_count,
        "fallback_count":  fallback_count,
        "error_count":     errors,
        "total_latency":   total_latency,
        "processed_at":    datetime.now().isoformat(),
        "sentiment_counts": processed_df["sentiment"].value_counts().to_dict(),
    }

    logger.info(f"Batch processing done — LLM: {llm_count}, "
                f"Fallback: {fallback_count}, took {total_latency}s")
    return {"processed_df": processed_df, "metrics": metrics}


def process_record(record: dict) -> dict:
    """
    Run sentiment analysis on a single stream record.
    Returns the record dict enriched with sentiment fields.
    """
    feedback = str(record.get("feedback", ""))
    rec_start = time.time()

    try:
        sentiment, source = _llm_sentiment(feedback)
    except Exception as e:
        logger.error(f"Error processing stream record {record.get('id')}: {e}")
        sentiment, source = rule_classify(feedback), "Rule-Based"

    return {
        **record,
        "sentiment":          sentiment,
        "processing_source":  source,
        "processed_at":       datetime.now().isoformat(),
        "record_latency_sec": round(time.time() - rec_start, 4),
    }
