import pandas as pd

from src.processing.aggregate_complaints import aggregate_complaints_by_order


def _complaints_df(rows):
    return pd.DataFrame(rows, columns=["complaint_id", "order_id", "complaint_type", "complaint_date"])


def test_single_complaint_per_order():
    df = _complaints_df([
        {"complaint_id": 1, "order_id": "ORD-1", "complaint_type": "missing_item", "complaint_date": "2026-07-05"},
    ])

    result = aggregate_complaints_by_order(df)

    assert len(result) == 1
    row = result[result["order_id"] == "ORD-1"].iloc[0]
    assert row["complaint_count"] == 1
    assert row["complaint_types"] == "missing_item"


def test_multiple_complaints_same_order_are_aggregated():
    df = _complaints_df([
        {"complaint_id": 1, "order_id": "ORD-1", "complaint_type": "missing_item", "complaint_date": "2026-07-05"},
        {"complaint_id": 2, "order_id": "ORD-1", "complaint_type": "late_delivery", "complaint_date": "2026-07-06"},
    ])

    result = aggregate_complaints_by_order(df)

    assert len(result) == 1  # one row for ORD-1, not two
    row = result[result["order_id"] == "ORD-1"].iloc[0]
    assert row["complaint_count"] == 2
    assert row["complaint_types"] == "late_delivery,missing_item"  # sorted, comma-joined


def test_duplicate_complaint_type_same_order_counted_but_not_repeated_in_types():
    df = _complaints_df([
        {"complaint_id": 1, "order_id": "ORD-1", "complaint_type": "missing_item", "complaint_date": "2026-07-05"},
        {"complaint_id": 2, "order_id": "ORD-1", "complaint_type": "missing_item", "complaint_date": "2026-07-06"},
    ])

    result = aggregate_complaints_by_order(df)

    row = result[result["order_id"] == "ORD-1"].iloc[0]
    assert row["complaint_count"] == 2  # both complaints counted
    assert row["complaint_types"] == "missing_item"  # but type listed once


def test_orders_with_no_complaints_are_absent_from_result():
    # This function only returns orders that HAVE complaints -- the
    # caller is responsible for filling in zero-complaint orders.
    df = _complaints_df([
        {"complaint_id": 1, "order_id": "ORD-1", "complaint_type": "missing_item", "complaint_date": "2026-07-05"},
    ])

    result = aggregate_complaints_by_order(df)

    assert "ORD-2" not in result["order_id"].values


def test_empty_complaints_returns_empty_result():
    df = _complaints_df([])

    result = aggregate_complaints_by_order(df)

    assert len(result) == 0
    assert list(result.columns) == ["order_id", "complaint_count", "complaint_types"]
