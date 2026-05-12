# AI Customer Feedback Monitoring System
### with Data Observability

A beginner-friendly, fully local, end-to-end system that processes customer
feedback through **two separate pipelines** — a CSV batch pipeline and a
real-time JSON stream pipeline — with AI sentiment analysis, validation, and
data observability.

---

## Project Architecture

```
project/
├── data/
│   ├── feedback.csv           ← 10-user batch dataset
│   └── stream_feedback.json   ← 10-user stream dataset
├── logs/
│   └── app.log
├── output/
│   ├── processed/             ← sentiment results, observability reports
│   └── validation/            ← valid/invalid records, validation reports
├── ingestion/
│   ├── batch_ingestor.py      ← reads CSV
│   └── stream_ingestor.py     ← reads JSON
├── validation/
│   └── validator.py           ← schema / null / duplicate / type checks
├── processing/
│   ├── sentiment_processor.py ← LLM primary + rule-based fallback
│   └── rule_based.py          ← keyword-based fallback classifier
├── observability/
│   └── observability.py       ← freshness, volume, quality, lineage
├── stream/
│   └── stream_simulator.py    ← drip-feeds 1 record every 5 seconds
├── dashboard/
│   ├── batch_dashboard.py     ← Streamlit batch UI
│   └── stream_dashboard.py    ← Streamlit stream UI (auto-refreshes)
├── utils/
│   ├── logger.py              ← shared logging (file + console)
│   └── file_utils.py          ← CSV / JSON read-write helpers
├── llm_config.py              ← configure your LLM here
├── main.py                    ← CLI batch runner
└── requirements.txt
```

---

## Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your LLM
Open `llm_config.py` and set your API key and endpoint.

**Option A — Environment variables (recommended)**
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # or any compatible URL
export LLM_MODEL="gpt-4o-mini"
```

**Option B — Edit llm_config.py directly**
```python
API_KEY   = "sk-your-key-here"
BASE_URL  = "https://api.openai.com/v1"
LLM_MODEL = "gpt-4o-mini"
```

> **Works with:** OpenAI, Together.ai, Groq, local Ollama, or any
> OpenAI-compatible endpoint.  
> **Fallback:** If the LLM is unreachable the system automatically switches
> to rule-based keyword classification — no crash, no data loss.

---

## Running the Pipelines

### CLI batch run
```bash
python main.py
```

### Batch Dashboard
```bash
streamlit run dashboard/batch_dashboard.py
```
Open `http://localhost:8501` → click **Run Batch Processing**.

### Stream Dashboard
```bash
streamlit run dashboard/stream_dashboard.py
```
Open `http://localhost:8501` → click **Start Stream**.  
One new record is processed every 5 seconds.  
Click **Reset Stream** to start over.

---

## Pipeline Details

### 1 — CSV Batch Pipeline

```
feedback.csv
  → batch_ingestor  (load & inspect)
  → validator       (schema / null / duplicate / type)
  → sentiment_processor (LLM → rule-based fallback)
  → observability   (freshness / volume / quality / lineage)
  → batch_dashboard
```

**Triggered manually** via the dashboard button or `python main.py`.  
All 10 records are processed in one shot.

---

### 2 — JSON Stream Pipeline

```
stream_feedback.json
  → stream_ingestor (load all 10 events)
  → stream_simulator (drip-feeds 1 event every 5 sec)
      → validator   (per-record)
      → sentiment_processor
      → observability (updated on every tick)
  → stream_dashboard (auto-refreshes)
```

**Starts automatically** when you click Start Stream.

---

## Validation Layer

Every record (batch or stream) passes through these four checks **before** AI
processing:

| Check | What it looks for |
|---|---|
| **Schema** | required columns: id, user, feedback, timestamp, source |
| **Null** | empty/null feedback or timestamp |
| **Duplicate** | repeated id values |
| **Type** | id must be numeric |

Invalid records are **never dropped silently** — they are saved to
`output/validation/*_invalid_records.csv` and logged.

---

## Data Observability

After each pipeline run the system generates an observability report covering:

| Dimension | What is measured |
|---|---|
| **Freshness** | source file age in minutes |
| **Volume** | source vs valid vs processed record counts |
| **Schema** | missing columns |
| **Quality** | null feedback, empty rows, duplicates, quality score |
| **Processing** | avg/max latency, LLM vs fallback counts |
| **Lineage** | source file → pipeline stages → output file |

Reports are saved to `output/processed/*_observability_report.json`.

---

## Logging

All pipeline events are logged to `logs/app.log`:

- ingestion started / completed  
- validation failures & invalid record counts  
- LLM call success / failure  
- fallback activation  
- observability warnings  
- per-record processing latency  

---

## Dataset

**Batch (`data/feedback.csv`)** — 10 users, mixed sentiments:

| id | User | Sentiment |
|---|---|---|
| 1 | Ram | Negative (slow delivery) |
| 2 | John | Positive (great quality) |
| 3 | Priya | Negative (app crashes) |
| 4 | Sarah | Positive (helpful support) |
| 5 | Amit | Negative (order never arrived) |
| 6 | Emma | Positive (great experience) |
| 7 | Raj | Negative (slow website) |
| 8 | Lisa | Negative (damaged product) |
| 9 | Arjun | Positive (fast delivery) |
| 10 | Maria | Negative (confusing refund) |

**Stream (`data/stream_feedback.json`)** — 10 different users (IDs 101–110),
processed one at a time every 5 seconds.
