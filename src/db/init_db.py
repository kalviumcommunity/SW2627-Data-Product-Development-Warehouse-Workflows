"""
Creates (or re-creates) the warehouse_tracker SQLite database from schema.sql.

Usage:
    python -m src.db.init_db
    python -m src.db.init_db --db-path data/processed/warehouse.db
"""

import argparse
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DB_PATH = Path(__file__).parents[2] / "data" / "processed" / "warehouse.db"


def init_db(db_path: Path = DEFAULT_DB_PATH, schema_path: Path = SCHEMA_PATH) -> Path:
    """Create the SQLite DB at db_path using the DDL in schema_path.

    Safe to run multiple times: all statements in schema.sql use
    `IF NOT EXISTS`, so re-running this will not drop existing data.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

    return db_path


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a connection to the warehouse DB, creating it first if needed."""
    if not db_path.exists():
        init_db(db_path)
    return sqlite3.connect(db_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the warehouse_tracker SQLite DB.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Where to create the SQLite DB file (default: data/processed/warehouse.db)",
    )
    args = parser.parse_args()

    created_path = init_db(args.db_path)
    print(f"Initialized database at {created_path}")
