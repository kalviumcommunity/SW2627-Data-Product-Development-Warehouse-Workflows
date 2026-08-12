"""
Generates mock CSVs for local development and testing, standing in for the
warehouse's real prep_logs / packing_audits / complaints / workflow_reference
exports until (or unless) real data becomes available.

This is dev tooling, not part of the production pipeline -- it is not
imported by src/. Run it once to populate data/raw/, then build ingestion
and cleaning code against its output.

Usage:
    python scripts/generate_mock_data.py
    python scripts/generate_mock_data.py --orders 500 --seed 7

Deliberately injected data-quality issues (so ingestion/cleaning code has
real things to catch, mirroring PRD 6.1/6.2):
    - a few orders with a missing prep_end (order never finished prepping)
    - one duplicate order_id in prep_logs
    - one malformed timestamp string
    - a handful of orders referencing a station_id NOT in workflow_reference
      (orphaned foreign key)
    - a few missing accuracy_flag values
    - a couple of complaint_date values in an inconsistent format
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parents[1] / "data" / "raw"

WORKFLOWS = ["pack-and-ship", "bulk-restock", "express-pick"]
SHIFTS = ["AM", "PM", "overnight"]
COMPLAINT_TYPES = [
    "missing_item",
    "wrong_item",
    "damaged_item",
    "late_delivery",
    "other",
]


def build_workflow_reference(num_stations: int):
    rows = []
    for i in range(1, num_stations + 1):
        rows.append(
            {
                "station_id": f"STN-{i:02d}",
                "workflow_name": random.choice(WORKFLOWS),
                "shift_id": random.choice(SHIFTS),
            }
        )
    return rows


def random_timestamp(base_date: datetime, max_offset_minutes: int = 60 * 24 * 14):
    return base_date + timedelta(minutes=random.randint(0, max_offset_minutes))


def build_prep_logs(num_orders: int, station_ids: list[str]):
    rows = []
    base_date = datetime(2026, 7, 1)

    for i in range(1, num_orders + 1):
        order_id = f"ORD-{i:05d}"
        station_id = random.choice(station_ids)
        prep_start = random_timestamp(base_date)
        prep_minutes = random.randint(3, 45)
        prep_end = prep_start + timedelta(minutes=prep_minutes)

        rows.append(
            {
                "order_id": order_id,
                "station_id": station_id,
                "prep_start": prep_start.isoformat(),
                "prep_end": prep_end.isoformat(),
            }
        )

    # --- Deliberate data-quality issues ---

    # 1. A few orders never finished prepping (missing prep_end).
    for row in random.sample(rows, k=max(1, num_orders // 100)):
        row["prep_end"] = ""

    # 2. One duplicate order_id (simulates a double-scanned order).
    if len(rows) >= 2:
        dup = dict(rows[0])
        dup["order_id"] = rows[5]["order_id"] if len(rows) > 5 else rows[0]["order_id"]
        rows.append(dup)

    # 3. One malformed timestamp.
    if rows:
        rows[min(2, len(rows) - 1)]["prep_start"] = "07/02/2026 not-a-real-time"

    # 4. A handful of orders reference a station not in workflow_reference.
    for row in random.sample(rows, k=max(1, num_orders // 150)):
        row["station_id"] = "STN-99"  # intentionally not in workflow_reference

    return rows


def build_packing_audits(prep_log_rows: list[dict]):
    rows = []
    seen_orders = set()

    for row in prep_log_rows:
        order_id = row["order_id"]
        if order_id in seen_orders:
            continue  # one audit per unique order
        seen_orders.add(order_id)

        rows.append(
            {
                "order_id": order_id,
                "station_id": row["station_id"],
                "accuracy_flag": random.choices(
                    ["correct", "incorrect"], weights=[0.88, 0.12]
                )[0],
            }
        )

    # 5. A few missing accuracy_flag values (audit started but not completed).
    for row in random.sample(rows, k=max(1, len(rows) // 100)):
        row["accuracy_flag"] = ""

    return rows


def build_complaints(prep_log_rows: list[dict], packing_rows: list[dict]):
    rows = []
    complaint_id = 1

    # Complaints skew towards orders that were packed incorrectly, to create
    # a realistic signal for the failure-rate analytics later, plus some
    # complaints on correctly-packed orders (e.g. late delivery).
    incorrect_orders = {r["order_id"] for r in packing_rows if r["accuracy_flag"] == "incorrect"}
    correct_orders = {r["order_id"] for r in packing_rows if r["accuracy_flag"] == "correct"}

    for order_id in incorrect_orders:
        if random.random() < 0.7:
            rows.append(_complaint_row(complaint_id, order_id))
            complaint_id += 1

    for order_id in random.sample(sorted(correct_orders), k=max(1, len(correct_orders) // 15)):
        rows.append(_complaint_row(complaint_id, order_id))
        complaint_id += 1

    # 6. A couple of complaint_date values in an inconsistent format
    #    (most are ISO 8601; a couple are MM/DD/YYYY).
    for row in random.sample(rows, k=min(2, len(rows))):
        row["complaint_date"] = _to_us_date(row["complaint_date"])

    return rows


def _complaint_row(complaint_id: int, order_id: str):
    complaint_date = datetime(2026, 7, 1) + timedelta(days=random.randint(1, 20))
    return {
        "complaint_id": complaint_id,
        "order_id": order_id,
        "complaint_type": random.choice(COMPLAINT_TYPES),
        "complaint_date": complaint_date.date().isoformat(),
    }


def _to_us_date(iso_date: str) -> str:
    y, m, d = iso_date.split("-")
    return f"{m}/{d}/{y}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate mock warehouse CSVs.")
    parser.add_argument("--orders", type=int, default=300, help="Number of orders to generate")
    parser.add_argument("--stations", type=int, default=10, help="Number of stations to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR, help="Output directory")
    args = parser.parse_args()

    random.seed(args.seed)

    workflow_rows = build_workflow_reference(args.stations)
    station_ids = [r["station_id"] for r in workflow_rows]

    prep_rows = build_prep_logs(args.orders, station_ids)
    packing_rows = build_packing_audits(prep_rows)
    complaint_rows = build_complaints(prep_rows, packing_rows)

    write_csv(
        args.out_dir / "workflow_reference.csv",
        workflow_rows,
        ["station_id", "workflow_name", "shift_id"],
    )
    write_csv(
        args.out_dir / "prep_logs.csv",
        prep_rows,
        ["order_id", "station_id", "prep_start", "prep_end"],
    )
    write_csv(
        args.out_dir / "packing_audits.csv",
        packing_rows,
        ["order_id", "station_id", "accuracy_flag"],
    )
    write_csv(
        args.out_dir / "complaints.csv",
        complaint_rows,
        ["complaint_id", "order_id", "complaint_type", "complaint_date"],
    )

    print(f"Generated mock data in {args.out_dir}:")
    print(f"  workflow_reference.csv  ({len(workflow_rows)} rows)")
    print(f"  prep_logs.csv           ({len(prep_rows)} rows)")
    print(f"  packing_audits.csv      ({len(packing_rows)} rows)")
    print(f"  complaints.csv          ({len(complaint_rows)} rows)")


if __name__ == "__main__":
    main()
