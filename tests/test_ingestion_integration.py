"""
Integration tests for the ingestion layer as a whole -- exercising all
four readers together via read_all_sources(), rather than one at a time
as the individual per-source test files do.

Individual structural checks (missing columns, empty files, malformed
rows) already have dedicated coverage in:
    tests/test_ingestion_prep_logs.py
    tests/test_ingestion_packing_audits.py
    tests/test_ingestion_complaints.py
    tests/test_ingestion_workflow_reference.py

This file instead answers a different question: does the ingestion layer
work correctly as a *set* -- reading a full directory of realistic data,
and failing clearly if any one file in that set has a problem?
"""

import random
import sys
from pathlib import Path

import pytest

from src.ingestion import MissingColumnsError, read_all_sources

# scripts/ isn't a package -- see tests/test_generate_mock_data.py for why.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_mock_data import (  # noqa: E402
    build_complaints,
    build_packing_audits,
    build_prep_logs,
    build_workflow_reference,
    write_csv,
)

EXPECTED_KEYS = {"prep_logs", "packing_audits", "complaints", "workflow_reference"}


def _write_full_mock_dataset(data_dir: Path, num_orders=200, num_stations=10, seed=1):
    random.seed(seed)

    workflow_rows = build_workflow_reference(num_stations)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(num_orders, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    write_csv(data_dir / "workflow_reference.csv", workflow_rows, ["station_id", "workflow_name", "shift_id"])
    write_csv(data_dir / "prep_logs.csv", prep_rows, ["order_id", "station_id", "prep_start", "prep_end"])
    write_csv(data_dir / "packing_audits.csv", packing_rows, ["order_id", "station_id", "accuracy_flag"])
    write_csv(data_dir / "complaints.csv", complaint_rows, ["complaint_id", "order_id", "complaint_type", "complaint_date"])


def test_read_all_sources_returns_all_four_dataframes(tmp_path):
    _write_full_mock_dataset(tmp_path)

    sources = read_all_sources(tmp_path)

    assert set(sources.keys()) == EXPECTED_KEYS
    for name, df in sources.items():
        assert len(df) > 0, f"{name} should not be empty"


def test_read_all_sources_dataframes_have_correct_columns(tmp_path):
    _write_full_mock_dataset(tmp_path)

    sources = read_all_sources(tmp_path)

    assert list(sources["prep_logs"].columns) == ["order_id", "station_id", "prep_start", "prep_end"]
    assert list(sources["packing_audits"].columns) == ["order_id", "station_id", "accuracy_flag"]
    assert list(sources["complaints"].columns) == ["complaint_id", "order_id", "complaint_type", "complaint_date"]
    assert list(sources["workflow_reference"].columns) == ["station_id", "workflow_name", "shift_id"]


def test_read_all_sources_fails_clearly_when_one_file_is_missing(tmp_path):
    _write_full_mock_dataset(tmp_path)
    (tmp_path / "complaints.csv").unlink()  # remove just one of the four

    with pytest.raises(FileNotFoundError, match="complaints.csv"):
        read_all_sources(tmp_path)


def test_read_all_sources_fails_clearly_when_one_file_has_missing_column(tmp_path):
    _write_full_mock_dataset(tmp_path)
    # Corrupt just packing_audits.csv, leave the other three untouched.
    (tmp_path / "packing_audits.csv").write_text("order_id,station_id\nORD-1,STN-01\n")

    with pytest.raises(MissingColumnsError) as exc_info:
        read_all_sources(tmp_path)

    assert exc_info.value.source_name == "packing_audits.csv"
    assert "accuracy_flag" in exc_info.value.missing_columns


def test_read_all_sources_order_ids_overlap_across_sources(tmp_path):
    # Not a join yet (that's a later stage) -- but a basic sanity check
    # that the four files are actually describing the same set of orders,
    # which the mock generator is designed to guarantee.
    _write_full_mock_dataset(tmp_path)

    sources = read_all_sources(tmp_path)

    prep_order_ids = set(sources["prep_logs"]["order_id"])
    packing_order_ids = set(sources["packing_audits"]["order_id"])
    complaint_order_ids = set(sources["complaints"]["order_id"])

    assert packing_order_ids.issubset(prep_order_ids)
    assert complaint_order_ids.issubset(prep_order_ids)
