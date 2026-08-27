import sys
from pathlib import Path

import pandas as pd

from src.processing.clean_packing_audits import clean_packing_audits

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import build_packing_audits, build_prep_logs, build_workflow_reference  # noqa: E402


def _raw_packing_audits_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["order_id", "station_id", "accuracy_flag"])


def test_correct_flag_is_valid():
    df = _raw_packing_audits_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "correct"},
    ])

    cleaned = clean_packing_audits(df)

    assert cleaned.loc[0, "accuracy_valid"] == True  # noqa: E712


def test_incorrect_flag_is_valid():
    df = _raw_packing_audits_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "incorrect"},
    ])

    cleaned = clean_packing_audits(df)

    assert cleaned.loc[0, "accuracy_valid"] == True  # noqa: E712


def test_missing_flag_is_flagged_not_dropped():
    df = _raw_packing_audits_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": ""},
    ])

    cleaned = clean_packing_audits(df)

    assert len(cleaned) == 1  # row is kept
    assert cleaned.loc[0, "accuracy_valid"] == False  # noqa: E712


def test_unrecognized_flag_value_is_flagged():
    # Defensive: any value other than the two expected ones should be
    # treated the same as missing, not silently accepted.
    df = _raw_packing_audits_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "unknown"},
    ])

    cleaned = clean_packing_audits(df)

    assert cleaned.loc[0, "accuracy_valid"] == False  # noqa: E712


def test_clean_packing_audits_does_not_mutate_input():
    df = _raw_packing_audits_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "correct"},
    ])
    original_columns = list(df.columns)

    clean_packing_audits(df)

    assert list(df.columns) == original_columns


def test_clean_packing_audits_against_real_mock_data():
    import random

    random.seed(1)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    df = pd.DataFrame(packing_rows, columns=["order_id", "station_id", "accuracy_flag"])

    cleaned = clean_packing_audits(df)

    assert len(cleaned) == len(df)  # no rows dropped
    assert (~cleaned["accuracy_valid"]).sum() > 0  # the seeded missing flags are caught
    assert cleaned["accuracy_valid"].sum() > 0  # most still valid
