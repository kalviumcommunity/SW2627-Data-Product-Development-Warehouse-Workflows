"""
Reader for complaints.csv.

One row per complaint, showing what went wrong after delivery:
complaint_id, order_id, complaint_type, complaint_date.

Unlike prep_logs and packing_audits, an order can have zero, one, or
multiple complaints -- this file is not one-row-per-order.

This module only reads and validates structure -- it does NOT clean data
(e.g. it won't normalize the inconsistent complaint_date formats seeded
by scripts/generate_mock_data.py, some ISO 8601, some MM/DD/YYYY).
Cleaning is handled separately, so bad/inconsistent rows are still
readable here and can be inspected/handled deliberately downstream
rather than silently altered at read time.
"""

from pathlib import Path

import pandas as pd

from src.ingestion.validation import validate_columns

SOURCE_NAME = "complaints.csv"
EXPECTED_COLUMNS = ["complaint_id", "order_id", "complaint_type", "complaint_date"]


def read_complaints(path: Path) -> pd.DataFrame:
    """Read and structurally validate complaints.csv.

    Raises:
        FileNotFoundError: if path does not exist.
        MissingColumnsError: if any expected column is missing.

    Returns:
        The raw DataFrame, unmodified aside from being loaded -- values
        (including inconsistently-formatted dates) are not cleaned,
        parsed, or typed here.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{SOURCE_NAME} not found at {path}")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)  # dtype=str +
    # keep_default_na=False: don't guess types and don't let pandas
    # silently convert blank cells to NaN -- same reasoning as the other
    # readers (see src/ingestion/prep_logs.py).

    validate_columns(df, EXPECTED_COLUMNS, SOURCE_NAME)

    return df
