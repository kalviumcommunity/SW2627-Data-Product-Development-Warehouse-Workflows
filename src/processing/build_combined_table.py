"""
Builds the full combined table: prep_logs + packing_audits (already
joined by join_prep_and_packing) with workflow_reference and complaints
joined in on top.

This is the table the analytics stage will actually query -- one row per
unique order, enriched with which workflow/shift handled it and how many
complaints (if any) it received.
"""

import pandas as pd

from src.processing.aggregate_complaints import aggregate_complaints_by_order
from src.processing.join_prep_and_packing import join_prep_and_packing


def join_workflow_reference(prep_packing_df: pd.DataFrame, workflow_df: pd.DataFrame) -> pd.DataFrame:
    """Left-join workflow/shift info onto the prep+packing table.

    Joins on the prep_logs side's station_id (station_id_prep), since
    that's the canonical station for the order -- packing_audits'
    station_id_packing might disagree (see station_id_mismatch from
    join_prep_and_packing) and shouldn't be used as the join key here.

    A station_id that doesn't exist in workflow_reference (e.g. the
    orphaned STN-99 seeded in mock data) is not an error at this stage --
    it's flagged via workflow_found=False so it stays visible rather than
    silently disappearing or crashing the join.

    Args:
        prep_packing_df: output of join_prep_and_packing().
        workflow_df: raw or cleaned workflow_reference DataFrame
            (station_id, workflow_name, shift_id).

    Returns:
        prep_packing_df with workflow_name, shift_id, and a
        workflow_found bool column added.
    """
    merged = prep_packing_df.merge(
        workflow_df,
        left_on="station_id_prep",
        right_on="station_id",
        how="left",
        suffixes=("", "_workflow_ref"),
    )

    merged["workflow_found"] = merged["workflow_name"].notna()

    # station_id from workflow_reference is now redundant with
    # station_id_prep (that's what we joined on) -- drop it to avoid a
    # confusing third station_id-ish column.
    merged = merged.drop(columns=["station_id"])

    return merged


def build_combined_table(
    prep_df: pd.DataFrame,
    packing_df: pd.DataFrame,
    complaints_df: pd.DataFrame,
    workflow_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build the full combined table from all four cleaned/raw sources.

    Args:
        prep_df: cleaned prep_logs (output of clean_prep_logs()).
        packing_df: cleaned packing_audits (output of clean_packing_audits()).
        complaints_df: raw or cleaned complaints (order_id, complaint_type, ...).
        workflow_df: raw or cleaned workflow_reference (station_id,
            workflow_name, shift_id).

    Returns:
        One row per unique order_id, with prep/packing/workflow columns
        plus complaint_count (0 for orders with no complaints) and
        complaint_types ("" for orders with no complaints).
    """
    combined = join_prep_and_packing(prep_df, packing_df)
    combined = join_workflow_reference(combined, workflow_df)

    complaint_summary = aggregate_complaints_by_order(complaints_df)
    combined = combined.merge(complaint_summary, on="order_id", how="left")

    # Orders with zero complaints have no row in complaint_summary, so
    # the merge above leaves NaN -- fill with the "no complaints" values
    # rather than leaving missing data that could be mistaken for "unknown".
    combined["complaint_count"] = combined["complaint_count"].fillna(0).astype(int)
    combined["complaint_types"] = combined["complaint_types"].fillna("")

    return combined
