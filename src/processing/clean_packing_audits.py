"""
Cleaning for packing_audits: flags rows where accuracy_flag is missing
(an audit that was started but never completed).

Same "flag, don't drop" philosophy as clean_prep_logs -- a row with a
missing accuracy_flag still has a real order_id/station_id that
shouldn't be lost just because the audit result itself is unknown.
"""

import pandas as pd

VALID_ACCURACY_FLAGS = {"correct", "incorrect"}


def clean_packing_audits(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows with a missing or unrecognized accuracy_flag.

    Args:
        df: raw packing_audits DataFrame, as returned by
            src.ingestion.read_packing_audits() (order_id, station_id,
            accuracy_flag -- all strings).

    Returns:
        A new DataFrame with the same rows, plus:
            - accuracy_valid: bool, True only if accuracy_flag is
              exactly "correct" or "incorrect"; False for missing or
              unrecognized values
    """
    df = df.copy()

    df["accuracy_valid"] = df["accuracy_flag"].isin(VALID_ACCURACY_FLAGS)

    return df
