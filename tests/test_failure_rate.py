import sys
from pathlib import Path

import pandas as pd
import pytest

from src.analytics.failure_rate import UNKNOWN_WORKFLOW_LABEL, complaints_and_failure_rate_by_workflow

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import (  # noqa: E402
    build_complaints,
    build_packing_audits,
    build_prep_logs,
    build_workflow_reference,
)
from src.processing import build_combined_table, clean_packing_audits, clean_prep_logs  # noqa: E402


def _combined_df(rows):
    """rows: list of dicts with order_id, workflow_name, complaint_count."""
    return pd.DataFrame(rows, columns=["order_id", "workflow_name", "complaint_count"])


def test_basic_failure_rate_calculation():
    df = _combined_df([
        {"order_id": "ORD-1", "workflow_name": "pack-and-ship", "complaint_count": 0},
        {"order_id": "ORD-2", "workflow_name": "pack-and-ship", "complaint_count": 1},
        {"order_id": "ORD-3", "workflow_name": "pack-and-ship", "complaint_count": 0},
        {"order_id": "ORD-4", "workflow_name": "pack-and-ship", "complaint_count": 0},
    ])

    result = complaints_and_failure_rate_by_workflow(df)

    row = result[result["workflow_name"] == "pack-and-ship"].iloc[0]
    assert row["total_orders"] == 4
    assert row["orders_with_complaint"] == 1
    assert row["total_complaints"] == 1
    assert row["failure_rate"] == pytest.approx(0.25)


def test_multiple_complaints_on_one_order_counts_as_one_failed_order():
    # An order with 2 complaints is still 1 failed order, not 2 --
    # failure_rate is about orders, not raw complaint volume.
    df = _combined_df([
        {"order_id": "ORD-1", "workflow_name": "pack-and-ship", "complaint_count": 2},
        {"order_id": "ORD-2", "workflow_name": "pack-and-ship", "complaint_count": 0},
    ])

    result = complaints_and_failure_rate_by_workflow(df)

    row = result[result["workflow_name"] == "pack-and-ship"].iloc[0]
    assert row["total_orders"] == 2
    assert row["orders_with_complaint"] == 1  # not 2
    assert row["total_complaints"] == 2  # raw count still reported
    assert row["failure_rate"] == pytest.approx(0.5)  # bounded at 0-1, not 1.0 from double-counting


def test_multiple_workflows_are_aggregated_separately():
    df = _combined_df([
        {"order_id": "ORD-1", "workflow_name": "pack-and-ship", "complaint_count": 1},
        {"order_id": "ORD-2", "workflow_name": "pack-and-ship", "complaint_count": 0},
        {"order_id": "ORD-3", "workflow_name": "bulk-restock", "complaint_count": 0},
        {"order_id": "ORD-4", "workflow_name": "bulk-restock", "complaint_count": 0},
    ])

    result = complaints_and_failure_rate_by_workflow(df)

    assert len(result) == 2
    pack_row = result[result["workflow_name"] == "pack-and-ship"].iloc[0]
    restock_row = result[result["workflow_name"] == "bulk-restock"].iloc[0]
    assert pack_row["failure_rate"] == pytest.approx(0.5)
    assert restock_row["failure_rate"] == pytest.approx(0.0)


def test_result_is_sorted_by_failure_rate_descending():
    df = _combined_df([
        {"order_id": "ORD-1", "workflow_name": "low-failure", "complaint_count": 0},
        {"order_id": "ORD-2", "workflow_name": "low-failure", "complaint_count": 0},
        {"order_id": "ORD-3", "workflow_name": "low-failure", "complaint_count": 0},
        {"order_id": "ORD-4", "workflow_name": "low-failure", "complaint_count": 0},
        {"order_id": "ORD-5", "workflow_name": "high-failure", "complaint_count": 1},
    ])

    result = complaints_and_failure_rate_by_workflow(df)

    assert result.iloc[0]["workflow_name"] == "high-failure"  # 100% failure rate, sorted first
    assert result.iloc[1]["workflow_name"] == "low-failure"


def test_orders_with_no_workflow_match_are_grouped_not_dropped():
    df = _combined_df([
        {"order_id": "ORD-1", "workflow_name": None, "complaint_count": 1},
        {"order_id": "ORD-2", "workflow_name": "pack-and-ship", "complaint_count": 0},
    ])

    result = complaints_and_failure_rate_by_workflow(df)

    assert len(result) == 2  # the "Unknown" bucket is a real row, not dropped
    unknown_row = result[result["workflow_name"] == UNKNOWN_WORKFLOW_LABEL].iloc[0]
    assert unknown_row["total_orders"] == 1
    assert unknown_row["orders_with_complaint"] == 1


def test_against_real_mock_data_full_pipeline():
    # End-to-end: generate mock data, run it through the full pipeline
    # (ingest-equivalent -> clean -> join -> analytics), and sanity-check
    # the output shape and math rather than exact numbers.
    import random

    random.seed(1)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    prep_df = pd.DataFrame(prep_rows, columns=["order_id", "station_id", "prep_start", "prep_end"])
    packing_df = pd.DataFrame(packing_rows, columns=["order_id", "station_id", "accuracy_flag"])
    complaints_df = pd.DataFrame(complaint_rows, columns=["complaint_id", "order_id", "complaint_type", "complaint_date"])
    workflow_df = pd.DataFrame(workflow_rows, columns=["station_id", "workflow_name", "shift_id"])

    combined = build_combined_table(
        clean_prep_logs(prep_df), clean_packing_audits(packing_df), complaints_df, workflow_df
    )

    result = complaints_and_failure_rate_by_workflow(combined)

    assert len(result) > 0
    assert (result["failure_rate"] >= 0).all()
    assert (result["failure_rate"] <= 1).all()
    assert result["total_orders"].sum() == combined["order_id"].nunique()
    # Sorted descending -- first row's rate should be >= last row's.
    assert result.iloc[0]["failure_rate"] >= result.iloc[-1]["failure_rate"]
