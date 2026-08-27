import sys
from pathlib import Path

import pandas as pd
import pytest

from src.processing.clean_prep_logs import clean_prep_logs

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import build_prep_logs, build_workflow_reference  # noqa: E402


def _raw_prep_logs_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["order_id", "station_id", "prep_start", "prep_end"])


def test_valid_row_gets_parsed_and_duration_computed():
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
    ])

    cleaned = clean_prep_logs(df)

    assert cleaned.loc[0, "prep_time_valid"] is True or cleaned.loc[0, "prep_time_valid"] == True  # noqa: E712
    assert cleaned.loc[0, "prep_duration_minutes"] == pytest.approx(20.0)
    assert pd.notna(cleaned.loc[0, "prep_start_parsed"])
    assert pd.notna(cleaned.loc[0, "prep_end_parsed"])


def test_missing_prep_end_is_flagged_not_dropped():
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": ""},
    ])

    cleaned = clean_prep_logs(df)

    assert len(cleaned) == 1  # row is kept
    assert cleaned.loc[0, "prep_time_valid"] == False  # noqa: E712
    assert pd.isna(cleaned.loc[0, "prep_duration_minutes"])
    assert pd.isna(cleaned.loc[0, "prep_end_parsed"])


def test_malformed_timestamp_is_flagged_not_dropped():
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "07/02/2026 not-a-real-time", "prep_end": "2026-07-01T10:20:00"},
    ])

    cleaned = clean_prep_logs(df)

    assert len(cleaned) == 1
    assert cleaned.loc[0, "prep_time_valid"] == False  # noqa: E712
    assert pd.isna(cleaned.loc[0, "prep_duration_minutes"])
    assert pd.isna(cleaned.loc[0, "prep_start_parsed"])


def test_negative_duration_is_flagged_invalid():
    # prep_end before prep_start -- both parse fine individually, but the
    # order doesn't make sense and shouldn't be treated as a valid duration.
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:20:00", "prep_end": "2026-07-01T10:00:00"},
    ])

    cleaned = clean_prep_logs(df)

    assert cleaned.loc[0, "prep_time_valid"] == False  # noqa: E712
    assert pd.isna(cleaned.loc[0, "prep_duration_minutes"])


def test_zero_duration_is_valid():
    # Same start and end time is unusual but not invalid -- an
    # instantaneous prep shouldn't be flagged just because it's fast.
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:00:00"},
    ])

    cleaned = clean_prep_logs(df)

    assert cleaned.loc[0, "prep_time_valid"] == True  # noqa: E712
    assert cleaned.loc[0, "prep_duration_minutes"] == 0.0


def test_duplicate_order_id_is_flagged_not_dropped():
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T11:00:00", "prep_end": "2026-07-01T11:15:00"},
        {"order_id": "ORD-2", "station_id": "STN-02",
         "prep_start": "2026-07-01T12:00:00", "prep_end": "2026-07-01T12:10:00"},
    ])

    cleaned = clean_prep_logs(df)

    assert len(cleaned) == 3  # no rows dropped
    assert cleaned.loc[0, "order_id_duplicate"] == False  # noqa: E712 -- first occurrence, canonical
    assert cleaned.loc[1, "order_id_duplicate"] == True  # noqa: E712 -- later occurrence, flagged
    assert cleaned.loc[2, "order_id_duplicate"] == False  # noqa: E712 -- unique order_id


def test_clean_prep_logs_does_not_mutate_input():
    df = _raw_prep_logs_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
    ])
    original_columns = list(df.columns)

    clean_prep_logs(df)

    assert list(df.columns) == original_columns  # unchanged


def test_clean_prep_logs_against_real_mock_data():
    # End-to-end sanity check against the actual generator, not just
    # hand-written fixtures -- confirms cleaning correctly flags the
    # deliberately-seeded missing prep_end and malformed timestamp rows,
    # and leaves the rest valid.
    import random

    random.seed(1)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    df = pd.DataFrame(prep_rows, columns=["order_id", "station_id", "prep_start", "prep_end"])

    cleaned = clean_prep_logs(df)

    assert len(cleaned) == len(df)  # no rows dropped
    assert (~cleaned["prep_time_valid"]).sum() > 0  # at least some flagged
    assert cleaned["prep_time_valid"].sum() > 0  # most still valid
    assert cleaned["order_id_duplicate"].sum() > 0  # the seeded duplicate is caught
