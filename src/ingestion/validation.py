"""
Shared validation logic for the ingestion layer (PRD 6.1: "check that each
file has the expected columns before using it").

Every per-source reader (prep_logs, packing_audits, complaints,
workflow_reference) calls validate_columns() right after loading its CSV,
before any downstream code touches the data. Keeping this in one place
means all four readers fail the same way, with the same error format.
"""

import pandas as pd


class MissingColumnsError(ValueError):
    """Raised when a source file is missing one or more required columns."""

    def __init__(self, source_name: str, missing_columns: list[str], found_columns: list[str]):
        self.source_name = source_name
        self.missing_columns = missing_columns
        self.found_columns = found_columns
        message = (
            f"{source_name}: missing required column(s) {missing_columns}. "
            f"Found columns: {found_columns}"
        )
        super().__init__(message)


def validate_columns(df: pd.DataFrame, expected_columns: list[str], source_name: str) -> None:
    """Raise MissingColumnsError if df is missing any expected column.

    Checks presence only, not order -- a reordered CSV is fine as long as
    every expected column exists. Does not check for *extra* columns,
    since an upstream export gaining a new column shouldn't break ingestion.
    """
    missing = [col for col in expected_columns if col not in df.columns]
    if missing:
        raise MissingColumnsError(
            source_name=source_name,
            missing_columns=missing,
            found_columns=list(df.columns),
        )
