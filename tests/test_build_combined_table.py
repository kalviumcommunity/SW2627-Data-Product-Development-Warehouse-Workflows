import sys
from pathlib import Path

import pandas as pd

from src.processing.build_combined_table import build_combined_table, join_workflow_reference
from src.processing.clean_packing_audits import clean_packing_audits
from src.processing.clean_prep_logs import clean_prep_logs
from src.processing.join_prep_and_packing import join_prep_and_packing

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import (  # noqa: E402
    build_complaints,
    build_packing_audits,
    build_prep_logs,
    build_workflow_reference,
)


def _prep_df(rows):
    return pd.DataFrame(rows, columns=["order_id", "station_id", "prep_start", "prep_end"])


def _packing_df(rows):
    return pd.DataFrame(rows, columns=["order_id", "station_id", "accuracy_flag"])


def _complaints_df(rows):
    return pd.DataFrame(rows, columns=["complaint_id", "order_id", "complaint_type", "complaint_date"])


def _workflow_df(rows):
    return pd.DataFrame(rows, columns=["station_id", "workflow_name", "shift_id"])


# --- join_workflow_reference ---

def test_join_workflow_reference_matches_known_station():
    prep_packing = join_prep_and_packing(
        clean_prep_logs(_prep_df([
            {"order_id": "ORD-1", "station_id": "STN-01",
             "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
        ])),
        clean_packing_audits(_packing_df([
            {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "correct"},
        ])),
    )
    workflow = _workflow_df([
        {"station_id": "STN-01", "workflow_name": "pack-and-ship", "shift_id": "AM"},
    ])

    result = join_workflow_reference(prep_packing, workflow)

    assert result.loc[0, "workflow_name"] == "pack-and-ship"
    assert result.loc[0, "shift_id"] == "AM"
    assert result.loc[0, "workflow_found"] == True  # noqa: E712


def test_join_workflow_reference_flags_orphaned_station():
    # station_id exists in prep_logs but not in workflow_reference --
    # should not crash or drop the row, just flag it.
    prep_packing = join_prep_and_packing(
        clean_prep_logs(_prep_df([
            {"order_id": "ORD-1", "station_id": "STN-99",
             "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
        ])),
        clean_packing_audits(_packing_df([
            {"order_id": "ORD-1", "station_id": "STN-99", "accuracy_flag": "correct"},
        ])),
    )
    workflow = _workflow_df([
        {"station_id": "STN-01", "workflow_name": "pack-and-ship", "shift_id": "AM"},
    ])

    result = join_workflow_reference(prep_packing, workflow)

    assert len(result) == 1  # row is kept, not dropped
    assert result.loc[0, "workflow_found"] == False  # noqa: E712
    assert pd.isna(result.loc[0, "workflow_name"])


# --- build_combined_table ---

def test_build_combined_table_basic_shape():
    prep = clean_prep_logs(_prep_df([
        {"order_id": "ORD-1", "station_id": "STN-01",
         "prep_start": "2026-07-01T10:00:00", "prep_end": "2026-07-01T10:20:00"},
        {"order_id": "ORD-2", "station_id": "STN-01",
         "prep_start": "2026-07-01T11:00:00", "prep_end": "2026-07-01T11:15:00"},
    ]))
    packing = clean_packing_audits(_packing_df([
        {"order_id": "ORD-1", "station_id": "STN-01", "accuracy_flag": "correct"},
        {"order_id": "ORD-2", "station_id": "STN-01", "accuracy_flag": "incorrect"},
    ]))
    complaints = _complaints_df([
        {"complaint_id": 1, "order_id": "ORD-2", "complaint_type": "wrong_item", "complaint_date": "2026-07-02"},
    ])
    workflow = _workflow_df([
        {"station_id": "STN-01", "workflow_name": "pack-and-ship", "shift_id": "AM"},
    ])

    combined = build_combined_table(prep, packing, complaints, workflow)

    assert len(combined) == 2  # one row per order

    ord1 = combined[combined["order_id"] == "ORD-1"].iloc[0]
    assert ord1["complaint_count"] == 0
    assert ord1["complaint_types"] == ""

    ord2 = combined[combined["order_id"] == "ORD-2"].iloc[0]
    assert ord2["complaint_count"] == 1
    assert ord2["complaint_types"] == "wrong_item"
    assert ord2["workflow_name"] == "pack-and-ship"


def test_build_combined_table_against_real_mock_data():
    import random

    random.seed(1)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    prep = clean_prep_logs(_prep_df(prep_rows))
    packing = clean_packing_audits(_packing_df(packing_rows))
    complaints = _complaints_df(complaint_rows)
    workflow = _workflow_df(workflow_rows)

    combined = build_combined_table(prep, packing, complaints, workflow)

    unique_order_count = prep["order_id"].nunique()
    assert len(combined) == unique_order_count

    # Every column from every stage should be present in the final table.
    expected_columns = {
        "order_id", "prep_duration_minutes", "prep_time_valid",
        "accuracy_flag", "accuracy_valid", "workflow_name", "shift_id",
        "workflow_found", "complaint_count", "complaint_types",
    }
    assert expected_columns.issubset(set(combined.columns))

    # The orphaned station_id (STN-99) seeded in mock data should show
    # up as workflow_found=False, not crash the join or vanish.
    assert (~combined["workflow_found"]).sum() > 0

    # No order should have a negative or missing complaint_count -- zero-
    # complaint orders should be filled in as 0, not left as NaN.
    assert combined["complaint_count"].isna().sum() == 0
    assert (combined["complaint_count"] >= 0).all()
