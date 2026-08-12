import csv
import sys
from pathlib import Path

# scripts/ isn't a package (it's dev tooling, not part of src/), so add it
# to sys.path directly rather than using a relative import.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from generate_mock_data import (  # noqa: E402
    build_complaints,
    build_packing_audits,
    build_prep_logs,
    build_workflow_reference,
    write_csv,
)


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_generator_produces_all_four_files(tmp_path):
    import random

    random.seed(1)

    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(50, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    write_csv(tmp_path / "workflow_reference.csv", workflow_rows, ["station_id", "workflow_name", "shift_id"])
    write_csv(tmp_path / "prep_logs.csv", prep_rows, ["order_id", "station_id", "prep_start", "prep_end"])
    write_csv(tmp_path / "packing_audits.csv", packing_rows, ["order_id", "station_id", "accuracy_flag"])
    write_csv(tmp_path / "complaints.csv", complaint_rows, ["complaint_id", "order_id", "complaint_type", "complaint_date"])

    for filename in ["workflow_reference.csv", "prep_logs.csv", "packing_audits.csv", "complaints.csv"]:
        assert (tmp_path / filename).exists()


def test_prep_logs_contains_known_issues():
    import random

    random.seed(1)

    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)

    order_ids = [r["order_id"] for r in prep_rows]
    assert len(order_ids) != len(set(order_ids)), "expected a deliberate duplicate order_id"

    missing_prep_end = [r for r in prep_rows if r["prep_end"] == ""]
    assert len(missing_prep_end) > 0, "expected some rows with missing prep_end"

    malformed = [r for r in prep_rows if "not-a-real-time" in r["prep_start"]]
    assert len(malformed) == 1, "expected exactly one malformed timestamp"

    orphaned = [r for r in prep_rows if r["station_id"] == "STN-99"]
    assert len(orphaned) > 0, "expected some rows referencing an orphaned station_id"
    assert "STN-99" not in station_ids


def test_packing_audits_contains_missing_flags():
    import random

    random.seed(1)

    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    packing_rows = build_packing_audits(prep_rows)

    missing_flags = [r for r in packing_rows if r["accuracy_flag"] == ""]
    assert len(missing_flags) > 0, "expected some missing accuracy_flag values"

    valid_flags = {"correct", "incorrect", ""}
    assert all(r["accuracy_flag"] in valid_flags for r in packing_rows)


def test_complaints_reference_real_orders():
    import random

    random.seed(1)

    workflow_rows = build_workflow_reference(5)
    station_ids = [r["station_id"] for r in workflow_rows]
    prep_rows = build_prep_logs(200, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    order_ids = {r["order_id"] for r in prep_rows}
    assert all(r["order_id"] in order_ids for r in complaint_rows)

    us_format_dates = [r for r in complaint_rows if "/" in r["complaint_date"]]
    assert len(us_format_dates) > 0, "expected a couple of inconsistent-format complaint_date values"
