# ingestion/stream_ingestor.py
import time
from utils.logger import get_logger
from utils.file_utils import read_json

logger = get_logger("stream_ingestor")


def ingest_stream(json_path: str) -> dict:
    """
    Load the full JSON list.  The stream simulator will drip-feed records one
    at a time — this just reads the source file.

    Returns:
        {
            "records": list[dict],
            "total": int,
            "source_file": str,
            "ingestion_time": float,
            "success": bool,
            "error": str | None,
        }
    """
    logger.info(f"Stream ingestion started — source: {json_path}")
    start = time.time()

    result = {
        "records": [],
        "total": 0,
        "source_file": json_path,
        "ingestion_time": 0.0,
        "success": False,
        "error": None,
    }

    try:
        data = read_json(json_path)
        if not isinstance(data, list):
            raise ValueError("Stream JSON must be a top-level list of objects.")
        result["records"] = data
        result["total"]   = len(data)
        result["success"] = True
        logger.info(f"Stream ingestion completed — {len(data)} events ready in "
                    f"{time.time()-start:.3f}s")
    except FileNotFoundError:
        msg = f"Stream JSON not found: {json_path}"
        result["error"] = msg
        logger.error(msg)
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Stream ingestion failed: {e}")

    result["ingestion_time"] = round(time.time() - start, 4)
    return result
