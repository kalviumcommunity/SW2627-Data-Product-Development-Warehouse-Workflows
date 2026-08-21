"""
Reader for workflow_reference.csv.

One row per station, showing which workflow and shift handled it:
station_id, workflow_name, shift_id.

Unlike the other three sources, this file has no seeded data-quality
issues in the mock generator -- it's treated as a clean lookup/reference
table. This module still validates its structure the same way as the
other readers, since a missing column here would be just as disruptive
downstream (every join to workflow/shift data depends on it).

This module only reads and validates structure -- it does NOT clean data.
"""

from pathlib import Path

import pandas as pd

from src.ingestion.validation import validate_columns

SOURCE_NAME = "workflow_reference.csv"
EXPECTED_COLUMNS = ["station_id", "workflow_name", "shift_id"]


def read_workflow_reference(path: Path) -> pd.DataFrame:
    """Read and structurally validate workflow_reference.csv.

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

    df = pd.read_csv(path, dtype=str, keep_default_na=False)  # dtype=str +
    # keep_default_na=False: don't guess types and don't let pandas
    # silently convert blank cells to NaN -- same reasoning as the other
    # readers (see src/ingestion/prep_logs.py).

    validate_columns(df, EXPECTED_COLUMNS, SOURCE_NAME)

    return df
