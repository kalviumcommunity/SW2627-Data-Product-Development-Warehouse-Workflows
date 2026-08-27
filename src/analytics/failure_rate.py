"""
Analytics: complaint counts and failure rate, aggregated by workflow.

Expects the full combined table (output of build_combined_table()) as
input -- this module only aggregates, it doesn't join or clean anything.

Design decision: failure rate is defined as
    (orders with at least one complaint) / (total orders)
rather than (total complaint count) / (total orders). An order with two
complaints is still one failed order, not two -- counting raw complaints
against orders would let a rate exceed 1.0 and wouldn't answer the
actual question ("what fraction of this workflow's orders failed?").
Total complaint count is still reported alongside, for visibility, since
it's useful context even though it isn't the rate itself.

Orders with no workflow match (workflow_found == False, e.g. the
orphaned station_id seeded in mock data) are grouped into an explicit
"Unknown (no workflow match)" bucket rather than being silently dropped
from the analysis -- they're real orders and a real gap in the
reference data, and both deserve to stay visible.
"""

import pandas as pd

UNKNOWN_WORKFLOW_LABEL = "Unknown (no workflow match)"


def complaints_and_failure_rate_by_workflow(combined_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate complaint counts and failure rate per workflow.

    Args:
        combined_df: the full combined table, as returned by
            build_combined_table() (must include workflow_name and
            complaint_count columns).

    Returns:
        One row per workflow (plus one row for orders with no workflow
        match, if any exist), with:
            - workflow_name: str
            - total_orders: int
            - orders_with_complaint: int
            - total_complaints: int (sum of complaint_count -- can be
              higher than orders_with_complaint if some orders have
              more than one complaint)
            - failure_rate: float, orders_with_complaint / total_orders

        Sorted by failure_rate descending, so the worst-performing
        workflow appears first.
    """
    df = combined_df.copy()

    df["workflow_name"] = df["workflow_name"].fillna(UNKNOWN_WORKFLOW_LABEL)
    df["has_complaint"] = df["complaint_count"] > 0

    grouped = df.groupby("workflow_name").agg(
        total_orders=("order_id", "count"),
        orders_with_complaint=("has_complaint", "sum"),
        total_complaints=("complaint_count", "sum"),
    )

    grouped["failure_rate"] = grouped["orders_with_complaint"] / grouped["total_orders"]

    grouped = grouped.sort_values("failure_rate", ascending=False).reset_index()

    return grouped
