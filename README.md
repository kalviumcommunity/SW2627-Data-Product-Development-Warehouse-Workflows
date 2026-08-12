# Warehouse Tracker

Warehouse Workflow Failure Intelligence Platform — connects order prep time,
packing accuracy, and delivery complaint data so operations leads can see
which warehouse workflow is causing the most delivery failures.

Built with Python, Pandas, SQL/SQLite, and Streamlit.

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