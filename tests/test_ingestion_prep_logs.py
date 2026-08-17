import sys
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.prep_logs import EXPECTED_COLUMNS, read_prep_logs
from src.ingestion.validation import MissingColumnsError, validate_columns

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import build_prep_logs, build_workflow_reference, write_csv


def _write_mock_prep_logs(tmp_path, num_orders=200, seed=1) -> Path:
    import random

    random.seed(seed)
    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(num_orders, station_ids)

    path = tmp_path / "prep_logs.csv"
    write_csv(path, prep_rows, EXPECTED_COLUMNS)
    return path


def test_read_prep_logs_returns_dataframe_with_expected_columns(tmp_path):
    path = _write_mock_prep_logs(tmp_path)

    df = read_prep_logs(path)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) > 0


def test_read_prep_logs_raises_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        read_prep_logs(missing_path)


def test_read_prep_logs_raises_on_missing_column(tmp_path):
    path = tmp_path / "prep_logs.csv"
    path.write_text("order_id,station_id,prep_start\nORD-1,STN-01,2026-07-01T10:00:00\n")

    with pytest.raises(MissingColumnsError) as exc_info:
        read_prep_logs(path)

    assert "prep_end" in exc_info.value.missing_columns


def test_read_prep_logs_raises_on_empty_file(tmp_path):
    path = tmp_path / "prep_logs.csv"
    path.write_text("")

    with pytest.raises(pd.errors.EmptyDataError):
        read_prep_logs(path)


def test_read_prep_logs_does_not_silently_drop_known_bad_rows(tmp_path):
    path = _write_mock_prep_logs(tmp_path, num_orders=200)

    df = read_prep_logs(path)

    assert (df["prep_end"] == "").sum() > 0
    assert df["order_id"].duplicated().sum() > 0
    assert (df["station_id"] == "STN-99").sum() > 0


def test_validate_columns_accepts_reordered_columns():
    df = pd.DataFrame(columns=["prep_end", "order_id", "prep_start", "station_id"])

    validate_columns(df, EXPECTED_COLUMNS, "prep_logs.csv")


def test_validate_columns_ignores_extra_columns():
    df = pd.DataFrame(columns=[*EXPECTED_COLUMNS, "some_new_upstream_column"])

    validate_columns(df, EXPECTED_COLUMNS, "prep_logs.csv")


def test_missing_columns_error_message_is_informative():
    df = pd.DataFrame(columns=["order_id", "station_id"])

    with pytest.raises(MissingColumnsError) as exc_info:
        validate_columns(df, EXPECTED_COLUMNS, "prep_logs.csv")

    assert exc_info.value.missing_columns == ["prep_start", "prep_end"]
    assert exc_info.value.source_name == "prep_logs.csv"
