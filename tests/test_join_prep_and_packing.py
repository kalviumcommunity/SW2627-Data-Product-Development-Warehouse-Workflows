import sys
from pathlib import Path

import pandas as pd

from src.processing.clean_packing_audits import clean_packing_audits
from src.processing.clean_prep_logs import clean_prep_logs
from src.processing.join_prep_and_packing import join_prep_and_packing

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import build_packing_audits, build_prep_logs, build_workflow_reference


def _prep_df(rows):
    return pd.DataFrame(rows, columns=["order_id", "station_id", "prep_start", "prep_end"])


def _packing_df(rows):
    return pd.DataFrame(rows, columns=["order_id", "station_id", "accuracy_flag"])


def test_basic_join_matches_rows_correctly():
    prep = clean_prep_logs(_prep_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
    ]))
    packing = clean_packing_audits(_packing_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "correct"},
    ]))

    joined = join_prep_and_packing(prep, packing)

    assert len(joined) == 1
    assert joined.loc[0, "order_id"] == "ORD-1"
    assert joined.loc[0, "accuracy_flag"] == "correct"
    assert joined.loc[0, "prep_duration_minutes"] == 20.0
    assert joined.loc[0, "station_id_mismatch"] == False


def test_join_excludes_duplicate_prep_rows():
    prep = clean_prep_logs(_prep_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T11:00:00", "prep_end": "2026-07-01T11:20:00"},
    ]))
    packing = clean_packing_audits(_packing_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "correct"},
    ]))

    joined = join_prep_and_packing(prep, packing)

    assert len(joined) == 1
    assert joined.loc[0, "prep_start"] == "2026-07-01T10:00:00"


def test_join_is_left_join_missing_packing_shows_as_nan():
    prep = clean_prep_logs(_prep_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
    ]))
    packing = clean_packing_audits(_packing_df([]))

    joined = join_prep_and_packing(prep, packing)

    assert len(joined) == 1
    assert pd.isna(joined.loc[0, "accuracy_flag"])


def test_join_flags_station_id_mismatch():
    prep = clean_prep_logs(_prep_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
    ]))
    packing = clean_packing_audits(_packing_df([
        {"order_id": "ORD-1", "station_id": "STN-99", "accuracy_flag": "correct"},
    ]))

    joined = join_prep_and_packing(prep, packing)

    assert joined.loc[0, "station_id_mismatch"] == True
    assert joined.loc[0, "station_id_prep"] == "STN-01"
    assert joined.loc[0, "station_id_packing"] == "STN-99"


def test_join_against_real_mock_data():
    import random

    random.seed(1)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    packing_rows = build_packing_audits(prep_rows)

    prep_raw = _prep_df(prep_rows)
    packing_raw = _packing_df(packing_rows)

    prep = clean_prep_logs(prep_raw)
    packing = clean_packing_audits(packing_raw)

    joined = join_prep_and_packing(prep, packing)

    unique_order_count = prep_raw["order_id"].nunique()
    assert len(joined) == unique_order_count
    assert "prep_duration_minutes" in joined.columns
    assert "accuracy_flag" in joined.columns
    assert "accuracy_valid" in joined.columns
