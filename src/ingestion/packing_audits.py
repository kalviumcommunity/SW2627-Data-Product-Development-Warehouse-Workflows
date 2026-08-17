"""
Reader for packing_audits.csv.

One row per order, showing whether the packed order matched what was
ordered: order_id, station_id, accuracy_flag.

This module only reads and validates structure -- it does NOT clean data
(e.g. it won't touch missing accuracy_flag values seeded by
scripts/generate_mock_data.py). Cleaning is handled separately, so bad
rows are still readable here and can be inspected/handled deliberately
downstream rather than silently dropped at read time.
"""

from pathlib import Path

import pandas as pd

from src.ingestion.validation import validate_columns

SOURCE_NAME = "packing_audits.csv"
EXPECTED_COLUMNS = ["order_id", "station_id", "accuracy_flag"]


def read_packing_audits(path: Path) -> pd.DataFrame:
    """Read and structurally validate packing_audits.csv.

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
