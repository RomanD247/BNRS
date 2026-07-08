#!/usr/bin/env python3
"""
Migration 001 (M7, CODE_REVIEW_FIX_PLAN.md Step 3).

Adds a partial unique index so SQLite itself refuses a second open
(rental_end IS NULL) rental for the same equipment_id — a backstop for the
app-layer check in crud.create_rental(), which closes the same race but only
within a single process/session.

models.py declares the same index for brand-new databases (create_all picks
it up automatically there); this script is only needed for a rental.db that
already existed before this migration was written, since create_all never
alters an existing table.

Safe to run more than once (CREATE UNIQUE INDEX IF NOT EXISTS). Aborts
without changing anything if duplicate open rentals already exist, since
SQLite cannot build a UNIQUE index over rows that would violate it - resolve
those manually (e.g. via the Admin > Rental History editor) and re-run.

Usage:
    python migrations/001_add_active_rental_unique_index.py [path/to/rental.db]
"""
import sqlite3
import sys


INDEX_NAME = "uq_active_rental_per_equipment"


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT equipment_id, COUNT(*) FROM rentals "
            "WHERE rental_end IS NULL GROUP BY equipment_id HAVING COUNT(*) > 1"
        )
        dupes = cur.fetchall()
        if dupes:
            print(f"ABORTED: {len(dupes)} equipment_id(s) have more than one open rental: {dupes}")
            print("Resolve these duplicates manually before re-running this migration.")
            sys.exit(1)

        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} "
            "ON rentals(equipment_id) WHERE rental_end IS NULL"
        )
        conn.commit()

        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (INDEX_NAME,))
        confirmed = cur.fetchone() is not None
        print(f"{'OK' if confirmed else 'FAILED'}: {INDEX_NAME} present on {db_path}: {confirmed}")
        if not confirmed:
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "rental.db"
    migrate(target)
