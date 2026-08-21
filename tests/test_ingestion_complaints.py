import sys
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.complaints import EXPECTED_COLUMNS, read_complaints
from src.ingestion.validation import MissingColumnsError

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import (  # noqa: E402
    build_complaints,
    build_packing_audits,
    build_prep_logs,
    build_workflow_reference,
    write_csv,
)


def _write_mock_complaints(tmp_path, num_orders=200, seed=1) -> Path:
    import random

    random.seed(seed)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(num_orders, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    path = tmp_path / "complaints.csv"
    write_csv(path, complaint_rows, EXPECTED_COLUMNS)
    return path


def test_read_complaints_returns_dataframe_with_expected_columns(tmp_path):
    path = _write_mock_complaints(tmp_path)

    df = read_complaints(path)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) > 0


def test_read_complaints_raises_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        read_complaints(missing_path)


def test_read_complaints_raises_on_missing_column(tmp_path):
    path = tmp_path / "complaints.csv"
    path.write_text("complaint_id,order_id,complaint_type\n1,ORD-1,missing_item\n")

    with pytest.raises(MissingColumnsError) as exc_info:
        read_complaints(path)

    assert "complaint_date" in exc_info.value.missing_columns


def test_read_complaints_raises_on_empty_file(tmp_path):
    path = tmp_path / "complaints.csv"
    path.write_text("")

    with pytest.raises(pd.errors.EmptyDataError):
        read_complaints(path)


def test_read_complaints_allows_multiple_rows_per_order(tmp_path):
    # complaints.csv is one-row-per-complaint, not one-row-per-order -- an
    # order can legitimately appear more than once.
    path = tmp_path / "complaints.csv"
    path.write_text(
        "complaint_id,order_id,complaint_type,complaint_date\n"
        "1,ORD-1,missing_item,2026-07-05\n"
        "2,ORD-1,late_delivery,2026-07-06\n"
    )

    df = read_complaints(path)

    assert len(df) == 2
    assert (df["order_id"] == "ORD-1").sum() == 2


def test_read_complaints_does_not_normalize_inconsistent_date_formats(tmp_path):
    # Reading is structural validation only -- the mock generator seeds a
    # couple of complaint_date values in MM/DD/YYYY instead of ISO 8601.
    # Normalizing them is cleaning's job, not this reader's.
    path = _write_mock_complaints(tmp_path, num_orders=200)

    df = read_complaints(path)

    us_format_dates = df["complaint_date"].str.contains("/")
    assert us_format_dates.sum() > 0

    iso_format_dates = df["complaint_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")
    assert iso_format_dates.sum() > 0
