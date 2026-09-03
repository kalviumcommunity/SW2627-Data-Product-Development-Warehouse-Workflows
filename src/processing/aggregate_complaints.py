"""
Aggregates complaints.csv from one-row-per-complaint into one-row-per-
order, so it can be joined onto the order-level combined table.

An order can have zero, one, or several complaints -- this collapses
that into per-order counts rather than trying to join complaints
directly (which would duplicate the order's prep/packing row once per
complaint).
"""

import pandas as pd


def aggregate_complaints_by_order(complaints_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse complaints.csv to one row per order_id.

    Args:
        complaints_df: cleaned/raw complaints DataFrame (order_id,
            complaint_type, ... -- complaint_id and complaint_date are
            not used here).

    Returns:
        One row per order_id that has at least one complaint, with:
            - complaint_count: int, how many complaints that order has
            - complaint_types: str, comma-separated distinct complaint
              types for that order (e.g. "missing_item,late_delivery")

        Orders with zero complaints are NOT included here -- the caller
        is expected to left-join this onto the full order list and treat
        missing rows as zero complaints (see build_combined_table()).
    """
    if complaints_df.empty:
        return pd.DataFrame(columns=["order_id", "complaint_count", "complaint_types"])

    grouped = complaints_df.groupby("order_id").agg(
        complaint_count=("complaint_type", "count"),
        complaint_types=("complaint_type", lambda types: ",".join(sorted(set(types)))),
    )

    return grouped.reset_index()
