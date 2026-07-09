#!/usr/bin/env python3
"""
Migration 002 (serialnum-default-false, CODE_REVIEW_FIX_PLAN.md Step 7).

models.py's Equipment.serialnum used to declare default=False. Any row
inserted without an explicit serialnum got the Python value False bound to a
TEXT-affinity SQLite column, which SQLite coerces to the string '0' at
insert time. This script clears that sentinel back to a real NULL so "no
serial number" is represented consistently.

Safe to run more than once (only rows literally equal to '0' are touched;
a genuine serial number of '0' is not a realistic value for this equipment,
but if one ever exists, this script would incorrectly clear it too - confirm
via the printed row list before running the update).

Usage:
    python migrations/002_clear_false_serialnum_sentinel.py [path/to/rental.db]
"""
import sqlite3
import sys


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_eq, name, serialnum FROM equipment WHERE serialnum = '0'")
        rows = cur.fetchall()
        print(f"Found {len(rows)} equipment row(s) with serialnum = '0':")
        for row in rows:
            print(f"  id_eq={row[0]} name={row[1]!r} serialnum={row[2]!r}")

        if not rows:
            print("OK: nothing to clean up")
            return

        cur.execute("UPDATE equipment SET serialnum = NULL WHERE serialnum = '0'")
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM equipment WHERE serialnum = '0'")
        remaining = cur.fetchone()[0]
        print(f"{'OK' if remaining == 0 else 'FAILED'}: cleared {len(rows)} row(s), {remaining} remaining with serialnum='0'")
        if remaining != 0:
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "rental.db"
    migrate(target)
