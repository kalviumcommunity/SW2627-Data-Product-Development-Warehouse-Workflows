import sys
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.packing_audits import EXPECTED_COLUMNS, read_packing_audits
from src.ingestion.validation import MissingColumnsError

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import (
    build_packing_audits,
    build_prep_logs,
    build_workflow_reference,
    write_csv,
)


def _write_mock_packing_audits(tmp_path, num_orders=200, seed=1) -> Path:
    import random

    random.seed(seed)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(num_orders, station_ids)
    packing_rows = build_packing_audits(prep_rows)

    path = tmp_path / "packing_audits.csv"
    write_csv(path, packing_rows, EXPECTED_COLUMNS)
    return path


def test_read_packing_audits_returns_dataframe_with_expected_columns(tmp_path):
    path = _write_mock_packing_audits(tmp_path)

    df = read_packing_audits(path)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) > 0


def test_read_packing_audits_raises_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        read_packing_audits(missing_path)


def test_read_packing_audits_raises_on_missing_column(tmp_path):
    path = tmp_path / "packing_audits.csv"
    path.write_text("order_id,station_id\nORD-1,STN-01\n")

    with pytest.raises(MissingColumnsError) as exc_info:
        read_packing_audits(path)

    assert "accuracy_flag" in exc_info.value.missing_columns


def test_read_packing_audits_raises_on_empty_file(tmp_path):
    path = tmp_path / "packing_audits.csv"
    path.write_text("")

    with pytest.raises(pd.errors.EmptyDataError):
        read_packing_audits(path)


def test_read_packing_audits_does_not_silently_drop_known_bad_rows(tmp_path):
    path = _write_mock_packing_audits(tmp_path, num_orders=200)

    df = read_packing_audits(path)

    assert (df["accuracy_flag"] == "").sum() > 0

    valid_or_blank = {"correct", "incorrect", ""}
    assert set(df["accuracy_flag"].unique()).issubset(valid_or_blank)
