# utils/file_utils.py
import os, json
import pandas as pd

BASE_DIR   = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PROC_DIR   = os.path.join(OUTPUT_DIR, "processed")
VAL_DIR    = os.path.join(OUTPUT_DIR, "validation")

for d in (PROC_DIR, VAL_DIR):
    os.makedirs(d, exist_ok=True)


# ── CSV helpers ───────────────────────────────────────────────────────────────
def save_csv(df: pd.DataFrame, filename: str, subdir: str = "processed") -> str:
    path = os.path.join(OUTPUT_DIR, subdir, filename)
    df.to_csv(path, index=False)
    return path

def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


# ── JSON helpers ──────────────────────────────────────────────────────────────
def save_json(data, filename: str, subdir: str = "processed") -> str:
    path = os.path.join(OUTPUT_DIR, subdir, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path

def load_json(path: str):
    with open(path) as f:
        return json.load(f)


# ── Generic read for any path ─────────────────────────────────────────────────
def read_json(path: str):
    return load_json(path)

def read_csv(path: str) -> pd.DataFrame:
    return load_csv(path)
