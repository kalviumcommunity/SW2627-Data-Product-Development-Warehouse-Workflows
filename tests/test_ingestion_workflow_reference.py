import sys
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.validation import MissingColumnsError
from src.ingestion.workflow_reference import EXPECTED_COLUMNS, read_workflow_reference

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import build_workflow_reference, write_csv  # noqa: E402


def _write_mock_workflow_reference(tmp_path, num_stations=10, seed=1) -> Path:
    import random

    random.seed(seed)
    workflow_rows = build_workflow_reference(num_stations)

    path = tmp_path / "workflow_reference.csv"
    write_csv(path, workflow_rows, EXPECTED_COLUMNS)
    return path


def test_read_workflow_reference_returns_dataframe_with_expected_columns(tmp_path):
    path = _write_mock_workflow_reference(tmp_path)

    df = read_workflow_reference(path)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) > 0


def test_read_workflow_reference_raises_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        read_workflow_reference(missing_path)


def test_read_workflow_reference_raises_on_missing_column(tmp_path):
    path = tmp_path / "workflow_reference.csv"
    path.write_text("station_id,workflow_name\nSTN-01,pack-and-ship\n")

    with pytest.raises(MissingColumnsError) as exc_info:
        read_workflow_reference(path)

    assert "shift_id" in exc_info.value.missing_columns


def test_read_workflow_reference_raises_on_empty_file(tmp_path):
    path = tmp_path / "workflow_reference.csv"
    path.write_text("")

    with pytest.raises(pd.errors.EmptyDataError):
        read_workflow_reference(path)


def test_read_workflow_reference_station_ids_are_unique(tmp_path):
    # workflow_reference.csv is one-row-per-station, so station_id should
    # never repeat. This isn't enforced by the reader itself (that's a
    # cleaning/validation concern for later), but it's worth confirming
    # the mock data actually reflects that assumption today.
    path = _write_mock_workflow_reference(tmp_path, num_stations=15)

    df = read_workflow_reference(path)

    assert df["station_id"].is_unique
