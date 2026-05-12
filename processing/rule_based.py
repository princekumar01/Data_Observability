# processing/rule_based.py
"""
Rule-based fallback sentiment analyser.
Used when the LLM is unavailable or returns an unexpected response.
"""
from utils.logger import get_logger

logger = get_logger("rule_based")

NEGATIVE_WORDS = {
    "slow", "bad", "terrible", "awful", "broken", "crashed", "crashing",
    "failed", "failure", "wrong", "damaged", "poor", "never", "worst",
    "horrible", "frustrating", "confused", "confusing", "disappointing",
    "charged", "lost", "missing", "delayed", "unclear", "painful",
}

POSITIVE_WORDS = {
    "good", "great", "excellent", "fantastic", "amazing", "love", "best",
    "perfect", "happy", "helpful", "fast", "quick", "smooth", "resolved",
    "outstanding", "wonderful", "superb", "awesome", "pleased", "satisfied",
}


def classify(text: str) -> str:
    """Return 'Positive', 'Negative', or 'Neutral' using keyword matching."""
    if not text or not isinstance(text, str):
        return "Neutral"

    words = set(text.lower().split())
    neg_hits = words & NEGATIVE_WORDS
    pos_hits = words & POSITIVE_WORDS

    if neg_hits and not pos_hits:
        sentiment = "Negative"
    elif pos_hits and not neg_hits:
        sentiment = "Positive"
    elif neg_hits and pos_hits:
        # Whichever side has more keyword hits wins
        sentiment = "Negative" if len(neg_hits) >= len(pos_hits) else "Positive"
    else:
        sentiment = "Neutral"

    logger.debug(f"Rule-based: '{text[:60]}' -> {sentiment} "
                 f"(neg={neg_hits}, pos={pos_hits})")
    return sentiment
