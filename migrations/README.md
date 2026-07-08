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
| 001 | `CREATE UNIQUE INDEX uq_active_rental_per_equipment ON rentals(equipment_id) WHERE rental_end IS NULL` (dedupe existing double-open rentals first) | M7 (Step 3) | Not yet applied |
| 002 | `UPDATE equipment SET serialnum = NULL WHERE serialnum = '0'` (optional cleanup, only if `serialnum-default-false` fix is adopted) | serialnum-default-false (Step 7) | Not yet applied / optional |
| 003 | Convert naive local timestamps to UTC-aware (only if `tz-naive-timestamps` fix is adopted — deferred per plan) | tz-naive-timestamps (Step 7) | Deferred, not scheduled |

## Migration log

_(empty — first entry goes here once migration 001 runs in Step 3)_
