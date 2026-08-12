-- Warehouse Tracker: raw data schema
-- Mirrors the four source CSVs (PRD section 4). One table per source file,
-- loaded as-is by the ingestion layer before any cleaning/joining happens.
-- Joining these into a single combined table is out of scope for this PR
-- (see PRD 6.2 / build order Week 3).

PRAGMA foreign_keys = ON;

-- station_id -> which workflow & shift handled that station.
-- One row per station, so station_id is a natural primary key.
CREATE TABLE IF NOT EXISTS workflow_reference (
    station_id      TEXT PRIMARY KEY,
    workflow_name   TEXT NOT NULL,
    shift_id        TEXT NOT NULL
);

-- One row per order: how long it took to prep.
-- order_id is treated as the primary key here since it is the first table
-- an order appears in; packing_audits and complaints reference it.
CREATE TABLE IF NOT EXISTS prep_logs (
    order_id        TEXT PRIMARY KEY,
    station_id      TEXT NOT NULL,
    prep_start      TEXT NOT NULL,  -- ISO 8601 timestamp, e.g. 2026-08-06T14:03:00
    prep_end        TEXT NOT NULL,
    FOREIGN KEY (station_id) REFERENCES workflow_reference (station_id)
);

-- One row per order: whether the packed order matched what was ordered.
CREATE TABLE IF NOT EXISTS packing_audits (
    order_id        TEXT PRIMARY KEY,
    station_id      TEXT NOT NULL,
    accuracy_flag   TEXT NOT NULL,  -- expected values: 'correct' | 'incorrect'
    FOREIGN KEY (order_id) REFERENCES prep_logs (order_id),
    FOREIGN KEY (station_id) REFERENCES workflow_reference (station_id)
);

-- One row per complaint. An order can have zero, one, or multiple
-- complaints, so this table is NOT keyed on order_id -- it gets its own
-- surrogate key instead.
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        TEXT NOT NULL,
    complaint_type  TEXT NOT NULL,
    complaint_date  TEXT NOT NULL,  -- ISO 8601 date, e.g. 2026-08-07
    FOREIGN KEY (order_id) REFERENCES prep_logs (order_id)
);

-- Indexes to support the joins/aggregations planned for later PRs
-- (combined table build in Week 3, complaint counts per workflow/station).
CREATE INDEX IF NOT EXISTS idx_prep_logs_station       ON prep_logs (station_id);
CREATE INDEX IF NOT EXISTS idx_packing_audits_order    ON packing_audits (order_id);
CREATE INDEX IF NOT EXISTS idx_packing_audits_station  ON packing_audits (station_id);
CREATE INDEX IF NOT EXISTS idx_complaints_order        ON complaints (order_id);
