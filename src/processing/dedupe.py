"""
Generic helper for flagging duplicate order_ids. Currently used by
prep_logs cleaning, since that's the only source with a seeded duplicate
-- but written generically since any order-keyed source could need it.

Same "flag, don't drop" philosophy as the rest of cleaning: the extra
occurrence is marked, not deleted, so a human (or a later join step) can
decide what to do with it rather than losing it silently.
"""

import pandas as pd


def flag_duplicate_order_ids(df: pd.DataFrame, order_id_col: str = "order_id") -> pd.DataFrame:
    """Flag rows sharing an order_id with an earlier row.

    The first occurrence of each order_id is left unflagged (it's treated
    as the canonical row); every later occurrence of that same order_id
    is flagged True.

    Args:
        df: DataFrame containing order_id_col.
        order_id_col: name of the column to check for duplicates.

    Returns:
        A new DataFrame with an added `order_id_duplicate` bool column.
    """
    df = df.copy()
    df["order_id_duplicate"] = df.duplicated(subset=[order_id_col], keep="first")
    return df
