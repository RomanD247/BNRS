# Manual DB migrations

`Base.metadata.create_all` (used by `database.py`) only adds missing **tables** — it
never adds columns, indexes, or changes defaults. Any schema change against the
committed `rental.db` must be applied by hand with a one-off script, tested against
a backup copy first, and documented here.

Policy (see `CODE_REVIEW_FIX_PLAN.md` ground rule 4):
1. Write the migration as a standalone `.sql` or `.py` script in this folder, named
   `NNN_short_description.sql` (or `.py`), where `NNN` is a zero-padded sequence
   number.
2. Run it against a **backup copy** of `rental.db` first and confirm the result.
3. Run it against the live `rental.db`.
4. Record the run (date, who/what ran it, row counts affected) in this file below.
5. Reference the migration file name in the commit message for the step that needed it.

## Pending migrations (tracked by the fix plan)

| # | Migration | Needed by | Status |
|---|---|---|---|
| 001 | `CREATE UNIQUE INDEX uq_active_rental_per_equipment ON rentals(equipment_id) WHERE rental_end IS NULL` (dedupe existing double-open rentals first) | M7 (Step 3) | ✅ Applied 2026-07-08 |
| 002 | `UPDATE equipment SET serialnum = NULL WHERE serialnum = '0'` (clears the `default=False` sentinel left by `serialnum-default-false`) | serialnum-default-false (Step 7) | ✅ Applied 2026-07-08 |
| 003 | Convert naive local timestamps to UTC-aware (only if `tz-naive-timestamps` fix is adopted — deferred per plan) | tz-naive-timestamps (Step 7) | Deferred, not scheduled |

## Migration log

- **2026-07-08 — 001_add_active_rental_unique_index.py** — Checked `rental.db` for existing duplicate open rentals first (`SELECT equipment_id, COUNT(*) ... HAVING COUNT(*) > 1`): zero found, so no dedupe was needed. Ran against a scratch copy of `rental.db` first and confirmed a manually-inserted duplicate open rental was correctly rejected with `UNIQUE constraint failed: rentals.equipment_id`. Then ran against the live `rental.db` (backed up immediately before, SHA-256 `1c05f6e...` matching the Step 0 backup) and confirmed the index exists via `sqlite_master`. Live DB SHA-256 after migration: `d5d710f...` (intentionally changed — this is a real schema change, unlike Steps 0-2 which left the DB byte-identical). `models.py` also declares the same index so any brand-new database gets it for free via `create_all`.
- **2026-07-08 — 002_clear_false_serialnum_sentinel.py** — Ran against a scratch copy of `rental.db` first: found and cleared 30 equipment rows with `serialnum = '0'` (all legacy rows, ids 128-157), confirmed 0 remaining. Ran the identical script against the live `rental.db` immediately after — same 30 rows, same result. `models.py`'s `Equipment.serialnum` column default changed from `False` to unset (`None`) in the same Step 7 commit, so this sentinel cannot reappear via `crud.create_equipment` or any other insert path going forward.
