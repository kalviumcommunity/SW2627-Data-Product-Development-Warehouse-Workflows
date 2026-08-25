"""
Cleaning for prep_logs: turns the raw string prep_start/prep_end columns
into real datetimes, and computes how long each order actually took to
prep.

Design decision: bad rows are flagged, not dropped. A row with a missing
or malformed timestamp still has real information in it (e.g. its
station_id, its order_id) that later stages -- like counting orders per
workflow -- shouldn't lose just because prep time couldn't be computed.
So this adds a `prep_time_valid` flag and leaves `prep_duration_minutes`
as missing (NaN) for those rows, rather than deleting the row outright.
Downstream code decides whether to exclude flagged rows from a given
calculation.

Handles, without dropping any row:
    - a malformed prep_start/prep_end value that can't be parsed as a date
    - a missing (blank) prep_start/prep_end value
    - a prep_end earlier than prep_start (data entry error -- negative
      duration doesn't mean anything and would corrupt an average)
    - a duplicate order_id (e.g. a double-scanned order) -- the first
      occurrence is treated as canonical, later ones are flagged
"""

import pandas as pd

from src.processing.dedupe import flag_duplicate_order_ids


def clean_prep_logs(df: pd.DataFrame) -> pd.DataFrame:
    """Parse prep_start/prep_end and compute prep duration.

    Args:
        df: raw prep_logs DataFrame, as returned by
            src.ingestion.read_prep_logs() (order_id, station_id,
            prep_start, prep_end -- all strings).

    Returns:
        A new DataFrame with the same rows, plus:
            - prep_start_parsed, prep_end_parsed: datetime64, NaT where
              the original value was missing or unparseable
            - prep_time_valid: bool, True only if both timestamps parsed
              AND prep_end is not before prep_start
            - prep_duration_minutes: float, minutes between prep_start
              and prep_end; NaN wherever prep_time_valid is False
            - order_id_duplicate: bool, True for every occurrence of an
              order_id after its first -- the first occurrence is treated
              as canonical
    """
    df = df.copy()

    df["prep_start_parsed"] = pd.to_datetime(df["prep_start"], errors="coerce")
    df["prep_end_parsed"] = pd.to_datetime(df["prep_end"], errors="coerce")

    both_parsed = df["prep_start_parsed"].notna() & df["prep_end_parsed"].notna()

    duration_minutes = (df["prep_end_parsed"] - df["prep_start_parsed"]).dt.total_seconds() / 60

    non_negative = duration_minutes >= 0
    non_negative = non_negative.fillna(False)

    df["prep_time_valid"] = both_parsed & non_negative
    df["prep_duration_minutes"] = duration_minutes.where(df["prep_time_valid"])

    df = flag_duplicate_order_ids(df)

    return df
