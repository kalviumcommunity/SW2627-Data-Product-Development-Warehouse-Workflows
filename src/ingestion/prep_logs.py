"""
Reader for prep_logs.csv (PRD section 4/6.1).

One row per order, showing how long it took to prepare:
order_id, station_id, prep_start, prep_end

This module only reads and validates structure -- it does NOT clean data
(e.g. it won't touch the malformed timestamp or missing prep_end values
seeded by scripts/generate_mock_data.py). Cleaning is a separate concern
(PRD 6.2), built in a later PR, so bad rows are still readable here and
can be inspected/handled deliberately downstream rather than silently
dropped at read time.
"""

from pathlib import Path

import pandas as pd

from src.ingestion.validation import validate_columns

SOURCE_NAME = "prep_logs.csv"
EXPECTED_COLUMNS = ["order_id", "station_id", "prep_start", "prep_end"]


def read_prep_logs(path: Path) -> pd.DataFrame:
    """Read and structurally validate prep_logs.csv.

    Raises:
        FileNotFoundError: if path does not exist.
        MissingColumnsError: if any expected column is missing.

    Returns:
        The raw DataFrame, unmodified aside from being loaded -- values
        are not cleaned, parsed, or typed here.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{SOURCE_NAME} not found at {path}")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    validate_columns(df, EXPECTED_COLUMNS, SOURCE_NAME)

    return df
