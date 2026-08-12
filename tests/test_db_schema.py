import sqlite3
from pathlib import Path

import pytest

from src.db.init_db import init_db

EXPECTED_TABLES = {
    "workflow_reference",
    "prep_logs",
    "packing_audits",
    "complaints",
}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_warehouse.db"


def test_init_db_creates_all_tables(db_path):
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        conn.close()

    table_names = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_init_db_is_idempotent(db_path):
    # Running init_db twice should not raise or drop existing data.
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO workflow_reference (station_id, workflow_name, shift_id) "
        "VALUES ('S1', 'pack-and-ship', 'AM')"
    )
    conn.commit()
    conn.close()

    init_db(db_path)  # re-run, should not wipe the row above

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM workflow_reference").fetchone()[0]
    finally:
        conn.close()

    assert count == 1


def test_foreign_keys_enforced(db_path):
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            # station_id 'DOES_NOT_EXIST' has no matching row in workflow_reference
            conn.execute(
                "INSERT INTO prep_logs (order_id, station_id, prep_start, prep_end) "
                "VALUES ('O1', 'DOES_NOT_EXIST', '2026-08-06T10:00:00', '2026-08-06T10:15:00')"
            )
            conn.commit()
    finally:
        conn.close()
