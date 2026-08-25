# Warehouse Tracker

Warehouse Workflow Failure Intelligence Platform — connects order prep time,
packing accuracy, and delivery complaint data so operations leads can see
which warehouse workflow is causing the most delivery failures.

## Team Roles

- **Backend** (ingestion, cleaning, joining, analytics, SQLite layer): this repo's `src/`
- **Frontend** (Streamlit dashboard): consumes backend outputs from `src/analytics/` and the SQLite DB

## Project Structure

```
warehouse-tracker/
├── src/
│   ├── ingestion/     # CSV readers + column validation for each data source
│   ├── processing/    # Data cleaning + joining into a combined table
│   ├── analytics/     # Complaint counts, failure rate calculations
│   └── db/            # SQLite schema + read/write helpers
├── tests/             # Unit tests (pytest)
├── data/
│   ├── raw/           # Input CSVs (prep_logs, packing_audits, complaints, workflow_reference) — gitignored
│   └── processed/     # Combined table / SQLite DB output — gitignored
├── notebooks/         # Exploratory analysis, not part of the production pipeline
├── requirements.txt
└── .gitignore
```

## Setup

```bash
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running Tests

```bash
pytest
```

## Ingestion

`src/ingestion/` reads and structurally validates each raw source before
any cleaning or joining happens. Each reader checks that its
expected columns are present, but does not clean or type-convert values —
that's a separate concern.

Implemented so far — all four raw sources, plus a consolidated entry point:

```python
from src.ingestion import read_all_sources

sources = read_all_sources("data/raw")
sources["prep_logs"]           # DataFrame
sources["packing_audits"]      # DataFrame
sources["complaints"]          # DataFrame
sources["workflow_reference"]  # DataFrame
```

Individual readers are still available directly if needed:

```python
from src.ingestion import read_prep_logs, read_packing_audits, read_complaints, read_workflow_reference
```

## Cleaning

`src/processing/` turns validated-but-raw data into something analysis-
ready. Cleaning never drops rows — it flags problems (e.g. a timestamp
that couldn't be parsed) so later stages can decide how to handle them,
rather than silently losing data.

Implemented so far: `clean_prep_logs()`, which parses `prep_start`/
`prep_end` into real datetimes and computes how long each order took to
prep. Adds `prep_time_valid` (False if a timestamp was missing,
unparseable, or `prep_end` came before `prep_start`) and
`prep_duration_minutes` (NaN for flagged rows).

```python
from src.ingestion import read_prep_logs
from src.processing import clean_prep_logs

raw_df = read_prep_logs("data/raw/prep_logs.csv")
cleaned_df = clean_prep_logs(raw_df)
```

## Generating mock data

Real warehouse export data isn't available for this project, so use the
generator to populate `data/raw/` with realistic mock CSVs before running
anything else:

```bash
python scripts/generate_mock_data.py
```

## Initializing the local database

```bash
python -m src.db.init_db
```

This creates `data/processed/warehouse.db` (gitignored) using the DDL in
`src/db/schema.sql`. Safe to re-run — it won't drop existing data.

## Status

This project runs entirely on generated mock data
there is no real warehouse data source. Raw-data schema is in place
(`workflow_reference`, `prep_logs`, `packing_audits`, `complaints`), CI
runs the test suite on every push/PR, the ingestion layer is complete
with readers for all four raw sources plus a consolidated
`read_all_sources()` entry point, and cleaning has started with
`clean_prep_logs()`
