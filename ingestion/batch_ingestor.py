# ingestion/batch_ingestor.py
import time
import pandas as pd
from utils.logger import get_logger
from utils.file_utils import read_csv

logger = get_logger("batch_ingestor")

REQUIRED_COLUMNS = {"id", "user", "feedback", "timestamp", "source"}


def ingest_batch(csv_path: str) -> dict:
    """
    Read the CSV file and return ingestion metadata + raw DataFrame.

    Returns:
        {
            "dataframe": pd.DataFrame,
            "record_count": int,
            "ingestion_time": float,   # seconds
            "source_file": str,
            "columns_found": list,
            "missing_columns": list,
            "success": bool,
            "error": str | None,
        }
    """
    logger.info(f"Batch ingestion started — source: {csv_path}")
    start = time.time()

    result = {
        "dataframe": pd.DataFrame(),
        "record_count": 0,
        "ingestion_time": 0.0,
        "source_file": csv_path,
        "columns_found": [],
        "missing_columns": [],
        "success": False,
        "error": None,
    }

    try:
        df = read_csv(csv_path)
        result["dataframe"]     = df
        result["record_count"]  = len(df)
        result["columns_found"] = list(df.columns)
        result["missing_columns"] = list(REQUIRED_COLUMNS - set(df.columns))
        result["success"]       = True
        logger.info(f"Batch ingestion completed — {len(df)} records loaded in "
                    f"{time.time()-start:.3f}s")
    except FileNotFoundError:
        msg = f"CSV file not found: {csv_path}"
        result["error"] = msg
        logger.error(msg)
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Batch ingestion failed: {e}")

    result["ingestion_time"] = round(time.time() - start, 4)
    return result
