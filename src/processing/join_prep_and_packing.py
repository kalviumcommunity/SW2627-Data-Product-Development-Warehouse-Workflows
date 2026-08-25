"""
Joins cleaned prep_logs and packing_audits into one order-level table.

Expects already-cleaned inputs (clean_prep_logs() / clean_packing_audits()
already applied) -- this module only joins, it doesn't clean.

Design decisions:
    - Duplicate order_ids in prep_logs are excluded before joining (only
      the canonical, first-seen row per order_id is kept), since a join
      on a duplicated key would fan out and silently double-count that
      order downstream. The flagged duplicate row itself isn't deleted
      from the cleaned DataFrame elsewhere -- it's just excluded from
      this particular join's output.
    - The join is a LEFT join from prep_logs: every prepped order should
      appear in the result, even if (for some reason) it has no matching
      packing audit yet. A missing audit shows up as NaN in the packing
      columns, not as a silently dropped row.
    - Both source tables have a station_id column. They *should* always
      agree (same order, same station), but if they don't, that's worth
      surfacing rather than silently picking one -- so both are kept
      (station_id_prep, station_id_packing) plus a station_id_mismatch
      flag.
"""

import pandas as pd


def join_prep_and_packing(prep_df: pd.DataFrame, packing_df: pd.DataFrame) -> pd.DataFrame:
    """Left-join cleaned prep_logs with cleaned packing_audits on order_id.

    Args:
        prep_df: cleaned prep_logs DataFrame (output of clean_prep_logs()),
            must include the order_id_duplicate column.
        packing_df: cleaned packing_audits DataFrame (output of
            clean_packing_audits()).

    Returns:
        One row per unique order_id from prep_df (duplicates excluded),
        with packing_audits columns attached. station_id appears twice,
        suffixed _prep and _packing, plus a station_id_mismatch bool.
    """
    canonical_prep = prep_df[~prep_df["order_id_duplicate"]].copy()

    merged = canonical_prep.merge(
        packing_df,
        on="order_id",
        how="left",
        suffixes=("_prep", "_packing"),
    )

    merged["station_id_mismatch"] = (
        merged["station_id_prep"].notna()
        & merged["station_id_packing"].notna()
        & (merged["station_id_prep"] != merged["station_id_packing"])
    )

    return merged
