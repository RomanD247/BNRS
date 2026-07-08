# Code Review Report — WenglorMEL Rental System (BNRS)

**Date:** 2026-07-07
**Branch:** `usb_scan` (uncommitted working-tree state included)
**Scope:** all project Python code (~12,000 lines): scanner subsystem, main app + GUI dialogs, data layer, web viewer, tests, dependencies, build/packaging, repo hygiene. Vendored venvs (`bnrs/`, `bnrs_old/`) and build outputs excluded.
**Method:** four focused review passes (scanner, UI, data layer, deps/tests/hygiene). Every **Critical** finding and the highest-impact **Major** findings were independently re-verified line-by-line in the source; all other findings cite exact file/line evidence found during review. **No code was changed.**
**Environment verified:** venv Python 3.11.9, SQLAlchemy 2.0.48, NiceGUI 3.8.0, hidapi 0.15.0, Pillow 12.1.1, pyscard 2.3.1, pywebview 6.1.

---

## Summary

| Severity | Count | Themes |
|---|---|---|
| Critical | 4 | broken scan-retry flow, dialogs that hang the scan futures, tests that mutate the live database and config |
| Major | 23 | soft-delete vs. unique-constraint collisions, no rollback handling, wrong-user/double rentals, name-based record matching, broken packaging, untracked core component |
| Minor | ~35 | resource leaks, race conditions, dead code, stale-session UI, logging/config robustness |
| Info | ~10 | dead legacy code, API-currency notes, duplication |

**The five issues most likely to hurt in production:**

1. **C3/C4** — running `pytest` (as CLAUDE.md suggests) writes fake rentals into the live `rental.db` and can silently mark a real active rental as returned; several tests also rewrite the live `scanner_config.json`.
2. **C1** — the USB scan error/retry flow is structurally broken: clicking "Retry" in any scanner error dialog runs a headless scan whose result is discarded, then crashes the background task.
3. **C2** — every scan/confirm dialog can be dismissed with ESC/outside-click, leaving the awaited future unresolved: in keyboard mode this leaks a permanent focus-stealing loop; in USB mode it locks the scanner until app restart.
4. **M2+M3+M4** — an `IntegrityError` (easily triggered by re-using a name/code of a soft-deleted row) or a SQLite lock timeout hits a bare `db.commit()` on one of 11 long-lived module sessions and **bricks the app** (`PendingRollbackError` on every later operation) until restart.
5. **M1 (data)** — launching the app from a different working directory silently creates a brand-new empty `rental.db` (and a default `scanner_config.json`) — all data appears to vanish.

---

## 1. Critical

### C1. USB scan retry flow resolves the future too early and double-resolves it — retried scans are lost and crash the task
[NfcScan.py:306-459](NfcScan.py#L306-L459), return at [NfcScan.py:475-480](NfcScan.py#L475-L480) — *(verified line-by-line)*

Every error path in `get_usb_hid_input` (permission error :313-314, connect failure :332-333, disconnect :402-403, timeout :418-419, corrupted data :435-436, generic :451-452) executes `dialog.close(); closed.set_result(None)` **before** awaiting the retry dialog. The caller's `await closed` (:478) resumes immediately and the workflow already reports failure. If the user then clicks **Retry**:

- the retry loop reconnects and scans with no visible dialog;
- a successful scan hits `closed.set_result(None)` again (:395) → `asyncio.InvalidStateError`;
- that is caught by the generic `except` (:447), which calls `closed.set_result(None)` a **third** time (:452) → second `InvalidStateError` → unhandled task exception; the scan is silently lost.

**Fix direction:** show the error/retry dialogs *inside* the scan loop before resolving `closed`; resolve `closed` exactly once when the loop truly ends; guard all `set_result` calls with `if not closed.done():`.

### C2. Scan/confirm dialogs are not persistent — ESC/outside-click leaves the awaited future unresolved and leaks resources
[NfcScan.py:247](NfcScan.py#L247), [NfcScan.py:496-544](NfcScan.py#L496-L544), [NfcScan.py:601-616](NfcScan.py#L601-L616), [NfcScan.py:1053](NfcScan.py#L1053), [NfcScan.py:1103](NfcScan.py#L1103) — *(verified: the only `.props('persistent')` dialog in the project is the admin password dialog at [main.py:573](main.py#L573))*

All scanner and confirmation dialogs are plain `ui.dialog()`, so Quasar closes them on ESC or outside click without running any handler — the `asyncio.Future` being awaited never resolves. Concrete consequences:

- **Keyboard mode:** `maintain_focus()` ([NfcScan.py:536-542](NfcScan.py#L536-L542)) loops `while not closed.done()`, refocusing a hidden input every 100 ms **forever** — the whole app permanently loses keyboard focus; every ESC'd scan leaks another loop.
- **USB user-selection dialog:** the background task loops `while not scanner_cancelled and not result.done()` ([NfcScan.py:738](NfcScan.py#L738)) holding the HID device open — the scanner is locked until app restart, and the rental workflow never resumes.
- **`get_usb_hid_input`:** a scan performed up to 30 s after dismissal still resolves the future, popping up the rental workflow unexpectedly.

**Fix direction:** `.props('persistent')` on scan dialogs, or subscribe to the dialog's hide/value-change event and resolve the future as "cancelled" there.

### C3. Test suite mutates the live, committed `rental.db`
[test_rental_workflow_integration.py:243](test_rental_workflow_integration.py#L243), [test_rental_workflow_integration.py:273](test_rental_workflow_integration.py#L273), [test_rental_workflow_integration.py:304-310](test_rental_workflow_integration.py#L304-L310) — *(verified line-by-line)*

The tests use the production `SessionLocal()` (→ `sqlite:///rental.db`):

- `:243` creates a **real rental row** for a real user/equipment; the ":273 cleanup" merely *returns* it — a fake completed rental is permanently added to history every run.
- `:304-310` picks `active_rentals[0]` — a **real, currently open rental** — and calls `return_equipment` on it **with no restoration**. Running this test silently marks someone's checked-out equipment as returned.

`git status` showing `M rental.db` and `M logs/scanner.log` confirms the suite has been run against live data. **Do not run bare `pytest` on a production machine until this is fixed.** Fix direction: pytest fixture that builds a temp SQLite file and overrides the engine/session (the isolation pattern already exists in `test_property_gui_config_persistence.py` for config).

### C4. Multiple tests rewrite the live `scanner_config.json` — some restore a hardcoded mode or nothing at all
[test_rental_workflow_integration.py:355-367](test_rental_workflow_integration.py#L355-L367), [test_nfc_scan_routing.py:38-91](test_nfc_scan_routing.py#L38-L91), [test_integration_nfc_workflow.py:83-95](test_integration_nfc_workflow.py#L83-L95), [test_property_mode_routing.py:234-240](test_property_mode_routing.py#L234-L240), plus `test_property_runtime_mode_switching.py`, `test_property_async_interface.py`

`CONFIG_FILE = "scanner_config.json"` is relative to the CWD, so tests run from the repo root rewrite the real config the app reads:

- `test_integration_nfc_workflow.py:95` and `test_rental_workflow_integration.py:367` "restore" a **hardcoded** `set_scanner_mode("usb_vendor")` — a keyboard-mode installation is silently flipped.
- `test_nfc_scan_routing.py` has **no try/finally** — an assertion failure leaves the mode flipped.
- `test_property_mode_routing.py:234-240` writes `"scanner_mode": "invalid_mode"` directly into the live file; a crash before the `finally` leaves the app with an invalid config.
- The hypothesis-based files rewrite the file up to 100× per property, racing any running app instance.

Only `test_property_gui_config_persistence.py` (lines 26-45) does this correctly (temp-dir redirect + restore) — use that pattern everywhere.

---

## 2. Major

### Data layer & database

**M1. `NameError` in `get_active_rentals_summary`** — [crud.py:400-401](crud.py#L400-L401) — *(verified)*
The `days, remainder = divmod(...)` line is commented out but the next line still reads `remainder` → guaranteed `NameError` on the first active rental. Currently latent (no callers found in the repo), but a landmine for any future report.

**M2. Relative DB path + `create_all` on import silently creates an empty database in the wrong directory** — [database.py:6-15](database.py#L6-L15), [main.py:901-909](main.py#L901-L909)
`sqlite:///rental.db` resolves against the process CWD, and `Base.metadata.create_all` runs on import. Launching the exe from a shortcut whose "Start in" differs from the install dir (or `python path\to\main.py` from elsewhere) manufactures a fresh empty DB with full schema — all data "vanishes", new data lands in the wrong file, and because the web-viewer subprocess inherits the same CWD, both processes agree and nothing looks broken. Same relative-path issue affects `scanner_config.json` ([scanner_config.py:23](scanner_config.py#L23) — settings silently reset to defaults, and `set_scanner_mode` writes a new file elsewhere) and `logs/` ([scanner_logging.py:17](scanner_logging.py#L17)). `fill_nfc_fields.py:17` duplicates the DB URL constant. **Fix direction:** anchor all paths to the application directory (`Path(__file__).parent` / `sys.executable`'s dir when frozen).

**M3. Unique constraints collide with soft-deleted rows — all duplicate pre-checks are blind to `status=False`** — [models.py:18](models.py#L18), [models.py:25](models.py#L25), [models.py:33](models.py#L33), [models.py:46](models.py#L46); checks at [crud.py:166-172](crud.py#L166-L172), [crud.py:823-827](crud.py#L823-L827), [gui/gui_addequip.py:73](gui/gui_addequip.py#L73), [gui/gui_adduser.py:81](gui/gui_adduser.py#L81), [gui/gui_changeUser.py:95](gui/gui_changeUser.py#L95), [gui/gui_changeEquip.py:91](gui/gui_changeEquip.py#L91), [main.py:765](main.py#L765)
Soft delete keeps the row (and its unique `name`/`nfc`) in the table, but every "already taken?" pre-check goes through `find_user_by_nfc`/`find_equipment_by_nfc`, which filter `status == True`. Re-creating a deleted Etype/Department name, or assigning a code that belonged to a deactivated user/equipment, passes validation and explodes as a raw `IntegrityError` at commit ("UNIQUE constraint failed"). `create_etype`/`create_department` ([crud.py:47-53](crud.py#L47-L53), [crud.py:87-93](crud.py#L87-L93)) have no duplicate check at all. Combined with M4, this can brick the session.

**M4. Almost no crud write rolls back on failure — one failed commit poisons the long-lived module sessions** — throughout [crud.py](crud.py) (`create_equipment`, `create_etype`, `create_department`, `create_user`, `update_user`, `create_rental` :218, `return_equipment` :242, `delete_rental`, `update_user_nfc`, …; only `update_rental` has try/rollback)
Every commit is bare. The app holds 11 module-level, never-recreated sessions ([main.py:33](main.py#L33), [NfcScan.py:22](NfcScan.py#L22), all 8 `gui/*.py` modules, [web_viewer/viewer_app.py:21](web_viewer/viewer_app.py#L21)). After any `IntegrityError` (M3) or `database is locked` (M5), the session stays in a failed transaction and **every subsequent operation raises `PendingRollbackError` until app restart**. Fix direction: wrap commits in try/except with `db.rollback()` (or a helper/context manager).

**M5. Two processes share one SQLite file with zero tuning — no WAL, no busy_timeout, no FK enforcement** — [database.py:9](database.py#L9)
The main app (writer) and the web viewer (reader, refreshing every 30 s per client) share `rental.db` in default rollback-journal mode. Lock contention beyond the driver's 5 s default surfaces as `OperationalError: database is locked` (feeding M4). SQLite foreign keys are OFF by default, and `rentals.user_id`/`equipment_id` are nullable ([models.py:53-54](models.py#L53-L54)) — orphaned rentals are representable. Fix direction: enable `journal_mode=WAL`, `busy_timeout`, and `PRAGMA foreign_keys=ON` via an engine `connect` event.

**M6. Soft-deleting rented equipment makes its open rental invisible and unreturnable** — [crud.py:37-44](crud.py#L37-L44), [crud.py:246-253](crud.py#L246-L253), [crud.py:199-206](crud.py#L199-L206), [gui/gui_changeEquip.py:218](gui/gui_changeEquip.py#L218)
Nothing prevents deactivating equipment that is currently on loan (including bulk deactivation via Etype). Once `status=False`, the open rental disappears from all "Currently Rented" lists (they join on `Equipment.status == True`) and scanning can no longer find the equipment (`find_equipment_by_nfc` filters status) — the rental stays open forever. Fix direction: block (or warn on) deactivation while `is_equipment_rented`.

**M7. No double-rental protection at any layer** — [crud.py:209-220](crud.py#L209-L220), [main.py:151-159](main.py#L151-L159), [gui/gui_changeRental.py](gui/gui_changeRental.py) — *(verified)*
`create_rental` inserts unconditionally; the manual rent dialog's Confirm has no `is_equipment_rented` check (only the scan workflow checks, [NfcScan.py:1049](NfcScan.py#L1049)); and there is no DB constraint (e.g., partial unique index on `rentals(equipment_id) WHERE rental_end IS NULL`). A double-click on Confirm, a stale Available list, or the rental editor clearing `rental_end` (which doesn't refresh the main screen) all create two open rentals for one device.

### Main app & GUI

**M8. Stale `state.selected_user` — rent dialog can rent to the wrong user** — [main.py:143-161](main.py#L143-L161) — *(verified)*
`state.selected_user` is global and cleared only on *successful* confirm. Open rent dialog for item A, pick "Alice", close via X; open the dialog for item B and click Confirm without selecting anyone → item B is silently rented to Alice. Fix direction: reset `state.selected_user = None` when the dialog opens (or make the selection local to the dialog).

**M9. Rental editor matches user/equipment by display name only** — [gui/gui_changeRental.py:182-187](gui/gui_changeRental.py#L182-L187), [gui/gui_changeRental.py:309-328](gui/gui_changeRental.py#L309-L328)
On save, `"Name (S/N: X)"` is stripped back to the bare name and the **first** name match wins; `User.name` is not unique and the user dropdown doesn't even disambiguate. Two devices named "Multimeter" → the edit saves against the wrong physical unit. Fix direction: map option → id (as the rent dialog's `users_dict` already does).

**M10. Rental editor cannot save edits to rentals of soft-deleted users/equipment** — [gui/gui_changeRental.py:130-131](gui/gui_changeRental.py#L130-L131), [gui/gui_changeRental.py:309-320](gui/gui_changeRental.py#L309-L320)
The form loads only active users/equipment, so fixing even a date/comment on a historical rental fails with "Selected user not found in system" once the user left the company. The record becomes edit-locked (only deletable).

**M11. Newly added equipment doesn't appear in the lists when no filter is active** — [main.py:116-131](main.py#L116-L131), [gui/gui_addequip.py:102-103](gui/gui_addequip.py#L102-L103) — *(verified)*
`update_lists` only re-queries the DB `if state.selected_etype_id is not None or state.name_filter`; otherwise it re-renders stale `state.available_equipment`. Adding a device with no filters set (the default) shows a success toast but no new card until "Refresh all data".

**M12. Duration columns sort lexicographically — the default sort of every report is wrong** — [gui/gui_reports.py:544-550](gui/gui_reports.py#L544-L550), sort defaults at [gui/gui_reports.py:208](gui/gui_reports.py#L208), 327, 449, 754; strings built at [crud.py:469](crud.py#L469), 566, 654, 722
Durations are unpadded `"D:HH:MM"` strings in sortable columns and all four statistics reports open sorted by them: `"9:05:00"` ranks above `"85:12:30"`. The history duration column also mixes in the string `"Active rental"`. Fix direction: sort on raw seconds (e.g., `:sort` custom comparator or a hidden numeric field).

**M13. Rental History reads through a never-expired module session — returned rentals keep showing "Not returned"** — [gui/gui_reports.py:21](gui/gui_reports.py#L21), [gui/gui_reports.py:540-563](gui/gui_reports.py#L540-L563)
`gui_reports.db` never commits/expires; SQLAlchemy's identity map returns previously loaded `Rental` objects without refreshing attributes. Return equipment on the main screen, reopen Rental History → the row still shows the old `rental_end`/"Active rental" until app restart. `full_refresh()` ([main.py:346](main.py#L346)) expires only `main.py`'s session.

**M14. Edit dialogs change code-bearing fields with no code regeneration or warning** — [gui/gui_changeUser.py:194-227](gui/gui_changeUser.py#L194-L227), [gui/gui_changeEquip.py:184-243](gui/gui_changeEquip.py#L184-L243)
Renaming a user/device or changing serialnum/department invalidates the printed Data Matrix label by design (payloads are built from those fields), but the edit paths neither regenerate the `nfc` payload nor warn that labels must be reprinted. Until "Update codes" is run the DB and the printed label silently diverge; after it runs, old labels scan as "not found".

**M15. Web-viewer subprocess is broken in frozen builds and double-spawns in dev** — [main.py:893-915](main.py#L893-L915)
Three stacked problems: (1) the PyInstaller command never bundles `web_viewer/`, so the shipped exe silently runs without the viewer; (2) if it were bundled, `sys.executable` in a frozen app is the rental exe itself, so `Popen([sys.executable, viewer_script])` would launch a second copy of the main app; (3) the spawn block runs under `if __name__ in {'__main__', '__mp_main__'}`, so the Windows native-mode child process starts a second viewer that races for port 8585. Related: [main.py:882](main.py#L882) hardcodes the LAN IP `http://172.20.124.60:8585` into the status label — wrong on any other host.

### Scanner subsystem

**M16. `configure_scanner.py` is completely nonfunctional — imports six functions that no longer exist** — [configure_scanner.py:15-22](configure_scanner.py#L15-L22) — *(verified against [scanner_config.py](scanner_config.py)'s actual exports)*
`get_effective_config`, `set_config_value`, `reset_config`, `save_user_config`, `load_user_config`, `is_legacy_mode` — none exist in the rewritten `scanner_config.py`; any invocation dies with `ImportError`. Its mode names (`'legacy_nfc'`) also predate the current schema. Fix or delete.

**M17. Cancel race in `get_usb_hid_input`: the blocking HID read keeps running after Cancel** — [NfcScan.py:252-259](NfcScan.py#L252-L259), [NfcScan.py:382-396](NfcScan.py#L382-L396)
`on_cancel` resolves the future, but the executor read (up to 30 s) is never interrupted and the `cancelled` flag is not re-checked when it returns: the HID device stays held, and if the user scans anyway, the success path calls `set_result` on the already-resolved future → the same `InvalidStateError` cascade as C1.

**M18. `except UnicodeDecodeError` is unreachable — corrupted scans are reported as "Scan Timeout"** — [usb_hid_scanner.py:245-250](usb_hid_scanner.py#L245-L250), [NfcScan.py:430-445](NfcScan.py#L430-L445)
`_parse_hid_report` catches the decode error internally and returns `None`, and `read_scan`'s own `except Exception` swallows everything else — so `show_corrupted_data_error` is dead code and the user gets the wrong dialog with misleading troubleshooting advice.

**M19. `read_scan` terminator logic truncates multi-report scans** — [usb_hid_scanner.py:176-194](usb_hid_scanner.py#L176-L194)
Accumulation stops as soon as `\n`, `\r`, or `\x00` appears anywhere in the buffer, but HID reports are fixed-length and NUL-padded — any payload longer than one report's payload is cut at the first report's padding, so a valid printed code scans as "Equipment not found". A scanner that never emits a terminator loops to timeout and the data is silently discarded. Also: config keys `read_size` and `encoding` ([scanner_config.py:33-34](scanner_config.py#L33-L34)) are ignored — `read(64)` and `'utf-8'` are hardcoded.

### Build, packaging & repo

**M20. `web_viewer/` — a documented core component — is not in version control** — *(verified: `?? web_viewer/` in `git status`)*
Cloning the repo produces an app that silently lacks the network viewer; the component has no history or backup. `CLAUDE.md` is also untracked.

**M21. The only committed PyInstaller spec is stale and broken; the working one is untracked** — `WenglorMEL Rental System 2.1.spec` (tracked) vs `WenglorMEL Rental System 2.1.4.spec` (untracked) — *(verified via `git ls-files`)*
The tracked 2.1 spec references a dead path (`...\Desktop\Apps\Rental System\...` — missing "My Projects"), has `binaries=[]` (no `libdmtx-64.dll` → Data Matrix encoding fails silently), and doesn't bundle `scanner_config.json`. The untracked 2.1.4 spec is the correct one. Version skew on top: the spec builds "2.1.4" while [main.py:918](main.py#L918) titles the window "2.1.5".

**M22. Runtime artifacts tracked in git; `.gitignore` contradicts the index** — `rental.db`, `logs/scanner.log`, 19 `__pycache__/*.pyc`, `scanner_config.json`, and the old `*.exe` are all tracked (several currently modified). `.gitignore` already lists `__pycache__/` and `*.db`, but ignore rules don't apply to tracked files. Missing patterns: `logs/`, `*.exe`, `.hypothesis/`, `.nicegui/`, `bnrs/`, `bnrs_old/`, `output*/`, `data/`. Fix direction: `git rm --cached` the artifacts, extend `.gitignore`. Note: `rental.db` in git is currently the only backup mechanism — set up a real backup before untracking it.

**M23. `requirements.txt` is incomplete and unbounded** — [requirements.txt](requirements.txt)
Missing dev/build deps actually used: `pytest` (9.0.2 installed), `pytest-asyncio` (1.3.0), `pyinstaller` (6.19.0) — a fresh environment can't run the tests or build. All pins are `>=` floors with no ceiling; NiceGUI proves the risk: the floor says `>=2.0.0` but the app is developed against 3.8.0 — a fresh install could land on any future major version. Recommend compatible-release pins (e.g., `nicegui>=3.8,<4`). `hypothesis` is a test-only dep listed as runtime.

---

## 3. Minor

### Scanner subsystem

- **Retry counter increments twice per connection retry** — [NfcScan.py:336-338](NfcScan.py#L336-L338) + [NfcScan.py:353-355](NfcScan.py#L353-L355) and [scanner_error_dialogs.py:126-130](scanner_error_dialogs.py#L126-L130): both the dialog's `retry_callback` and the caller's `if choice == "retry"` branch increment `retry_count`, so the user gets ~2 attempts instead of the intended 3.
- **`USBHIDScanner.connect()` leaks the opened HID handle** if `get_manufacturer_string()`/`get_product_string()` raise after a successful `open()` — all except branches set `self.device = None` without `close()` ([usb_hid_scanner.py:87-121](usb_hid_scanner.py#L87-L121)).
- **`load_config`'s nested-defaults merge is a no-op** — [scanner_config.py:144-151](scanner_config.py#L144-L151): `merged_config.update(config)` replaces the nested dict wholesale, then updates that same object with itself; missing nested keys (e.g. `timeout`) are not backfilled (currently masked by callers' `.get(..., default)`).
- **No `.done()` guards on dialog futures anywhere** — rapid double-click on any confirm/cancel raises `asyncio.InvalidStateError` ([NfcScan.py:1056-1063](NfcScan.py#L1056-L1063), [NfcScan.py:1108-1110](NfcScan.py#L1108-L1110), [scanner_error_dialogs.py:56-69](scanner_error_dialogs.py#L56-L69) etc.). `crud.return_equipment` is idempotent, so no double DB mutation — the damage is the unhandled exception.
- **`_check_connection` issues a USB control transfer every ~10 ms** for the whole read loop (~100 descriptor reads/s for up to 30 s) — [usb_hid_scanner.py:168-194](usb_hid_scanner.py#L168-L194).
- **`disconnect()` can run while the executor thread is inside `read_scan`** — task cancellation path in [NfcScan.py:796-806](NfcScan.py#L796-L806) closes the device under a thread that may be mid-`read()`; not guaranteed safe by hidapi.
- **`save_config` writes non-atomically** — [scanner_config.py:185-192](scanner_config.py#L185-L192): a crash mid-write leaves truncated JSON, which `load_config` then silently replaces with defaults (losing mode + custom VID/PID). Use temp-file + `os.replace`.
- **Blocking calls on the event loop** — `scanner.connect()` (blocking USB open) is called directly in async context at [NfcScan.py:307](NfcScan.py#L307) and [NfcScan.py:727](NfcScan.py#L727); every `get_scanner_mode()`/`get_usb_config()` call does synchronous file I/O from async handlers. A slow USB enumeration briefly freezes the UI.
- **Unknown `scanner_mode` silently disables scanning in the user-selection dialog** — [NfcScan.py:686-691](NfcScan.py#L686-L691), [NfcScan.py:780-793](NfcScan.py#L780-L793): unlike `get_nfc_input` (which falls back to keyboard, :582-587), a hand-edited/corrupt mode value yields a dialog that promises scanning while no scan path exists.
- **`setup_logging` clobbers the root logger and never rotates** — [scanner_logging.py:47-66](scanner_logging.py#L47-L66): `root_logger.handlers.clear()` removes everyone else's handlers; the plain `FileHandler` grows `logs/scanner.log` without bound (and it's in git, perpetually dirty); scanned payloads (containing user names) are logged at INFO.
- **Contradictory UX on keyboard fallback** — [NfcScan.py:340-359](NfcScan.py#L340-L359): choosing "Use Keyboard Mode" notifies "restart the scan" but the workflow simultaneously shows "Scanner not connected"; the scan is not auto-restarted in the new mode.

### Data layer

- **`Equipment.serialnum` has a boolean default on a String column** — [models.py:14](models.py#L14) `Column(String, default=False)`: an insert relying on the default stores `0`; `MatrixCode` then happily prints `{id}_{name}_0` payloads and the UI shows "S/N: 0". Typo for `None`.
- **Cross-table `nfc` payload ambiguity** — [MatrixCode.py:46](MatrixCode.py#L46) vs [MatrixCode.py:106](MatrixCode.py#L106): user `7_alpha_2` (id 7, name Alpha, dept 2) and equipment `7_alpha_2` (id 7, name Alpha, serial 2) are the identical string; uniqueness is per-table only, and which entity a scan resolves to depends on workflow lookup order. Low probability; a `u_`/`e_` prefix would eliminate it.
- **`update_equipment`/`update_etype`/`update_department` can never reactivate a soft-deleted row** — [crud.py:24-35](crud.py#L24-L35), [crud.py:67-75](crud.py#L67-L75), [crud.py:111-119](crud.py#L111-L119): each fetches via its status-filtered getter, so `status=True` restore silently no-ops. Only `update_user` got an escape hatch; the equipment GUI bypasses crud entirely. Truthiness checks (`if name:`) also make clearing a field impossible.
- **`update_user` mutates before validating** — [crud.py:157-172](crud.py#L157-L172): if the NFC-duplicate check raises, the already-applied name/department changes stay dirty in the long-lived session and are silently persisted by the next unrelated commit.
- **Statistics `outerjoin` immediately negated by a filter** — [crud.py:454-455](crud.py#L454-L455) (same in :641, :709): `.filter(subquery.c.total_seconds > 0)` turns the outer join into an inner join, so the explicit `"never rented"` branches (:471-473, :656-658, :723-725) are dead code and never-rented users/departments silently never appear.
- **Timezone-naive local timestamps distort durations across DST** — [models.py:55](models.py#L55), [crud.py:214](crud.py#L214) etc.: a rental spanning a DST transition is off by an hour; a return inside the fall-back fold can compute negative, which `duration_utils` silently clamps to `0:00:00`, masking the data problem.
- **`NOT IN` subquery vulnerable to a single NULL `equipment_id`** — [crud.py:282-302](crud.py#L282-L302): one rentals row with `equipment_id IS NULL, rental_end IS NULL` (possible: column nullable, FKs unenforced) instantly empties the "Available Equipment" list everywhere, with no error.
- **`database.py` runs with `echo=True`** — [database.py:9](database.py#L9): every SQL statement + parameters (names, comments) logged to stdout for the life of both processes.

### Main app & GUI

- **Dead "no selection" validation in both add dialogs** — [gui/gui_adduser.py:94-97](gui/gui_adduser.py#L94-L97), [gui/gui_addequip.py:87-90](gui/gui_addequip.py#L87-L90): compares the label against `'None'`, which it never contains (placeholder is "You must choose department!"), so submitting without a selection surfaces a raw backend error instead of the friendly warning.
- **Cancelled scan makes the form lie about the stored code** — [gui/gui_changeUser.py:89-103](gui/gui_changeUser.py#L89-L103), [gui/gui_changeEquip.py:85-99](gui/gui_changeEquip.py#L85-L99): the label switches to "Not set" while Apply keeps the old code in the DB; there is also no way to actually clear a code from these forms.
- **Return dialog always reports success** — [main.py:227-231](main.py#L227-L231): `return_equipment` no-ops on an already-returned rental, but the toast says "Equipment returned successfully!" regardless.
- **Department/Etype bulk status update commits before the rename commit** — [gui/gui_changeDep.py:150-159](gui/gui_changeDep.py#L150-L159), [gui/gui_changeEtype.py:141-150](gui/gui_changeEtype.py#L141-L150): if the second commit fails (e.g., rename hits the unique constraint), users/equipment are already flipped — partial update with a success toast already shown.
- **Sessions reused after their `with` block closed them** — [main.py:707-801](main.py#L707-L801) (`show_add_nfc_dialog`), [gui/gui_changeUser.py:95](gui/gui_changeUser.py#L95), [gui/gui_changeEquip.py:91](gui/gui_changeEquip.py#L91): dialog callbacks use `fresh_db` after `Session.close()` ran; works only because SQLAlchemy transparently reopens closed sessions — fragile and defeats the "fresh session" intent.
- **Stale module-level dropdown data in add dialogs** — [gui/gui_addequip.py:19](gui/gui_addequip.py#L19) (`data = load_etypes()` never refreshed): rename an equipment type → Add Device still offers the old name, and selecting it fails with "Equipment type X not found!".
- **Empty `ui.row` leaked on every cancelled scan** — [gui/gui_addequip.py:81-82](gui/gui_addequip.py#L81-L82), [gui/gui_adduser.py:88-90](gui/gui_adduser.py#L88-L90): copy-paste artifact wrapping a label assignment in a new row element.
- **Unbounded dialog accumulation** — all dialog factories create a new `ui.dialog()` on the shared auto-index page per open, and the edit dialogs auto-reopen themselves after each save (`ui.timer(0.1, ..., once=True)`); nothing is ever removed — a long-running kiosk session grows the DOM without bound.
- **`tkinter.Tk()` created in worker threads** — [main.py:443-459](main.py#L443-L459), [main.py:484-500](main.py#L484-L500), [gui/gui_changeUser.py:110-123](gui/gui_changeUser.py#L110-L123), [gui/gui_changeEquip.py:106-119](gui/gui_changeEquip.py#L106-L119): `pick_folder` runs via `run.io_bound`; Tk off the main thread is unsupported and can hang/crash sporadically.
- **Dead "zero rental time" filter duplicated 8×** — [gui/gui_reports.py:152](gui/gui_reports.py#L152) etc.: `str(...) != '0'` never matches (values are `"0:00:00"`), and the CRUD layer already filters `> 0`.
- **Admin gesture docstring contradicts the code** — [main.py:652-670](main.py#L652-L670): says "5 clicks within 0.4 s"; implementation is 3 clicks within 0.8 s. Hardcoded password `"supp"` at [main.py:643](main.py#L643) is a known issue (`#Change !password`).
- **Scanner settings dialog blocks the UI while opening** — [gui/gui_scanner_config.py:73](gui/gui_scanner_config.py#L73), [gui/gui_scanner_config.py:175](gui/gui_scanner_config.py#L175): connection check + device enumeration run synchronously during dialog build (the "Scanning for devices..." spinner is never visible); and if `update_usb_config` succeeds but `set_scanner_mode` fails, the config is half-saved while the user sees only "Failed to save configuration".

### Web viewer

- **One module-level session shared by every LAN client, forever** — [web_viewer/viewer_app.py:21](web_viewer/viewer_app.py#L21): freshness depends entirely on each client's 30 s `ui.timer` calling `db.expire_all()`; renamed/edited data can be up to 30 s stale (including on fresh page loads, due to the identity map), and a hard-deleted rental (`delete_rental`) between an `expire_all` and attribute access raises `ObjectDeletedError` for that client. Not a thread-safety violation (handlers run on the event loop) — but a fresh session per refresh would be simpler and correct.
- **Read-only by convention, not enforcement** — the viewer imports only read functions (verified), but the process opens the DB read-write and `import database` runs `create_all` there too. `sqlite:///file:rental.db?mode=ro&uri=true` would enforce it. It binds `0.0.0.0:8585` with a hardcoded `storage_secret='rental_viewer_secret_key_change_in_production'` ([web_viewer/viewer_app.py:381](web_viewer/viewer_app.py#L381)) and exposes full rental history (names) to the LAN — by design, but worth stating.

### Tests

- **`test_background_scanner.py` has zero effective coverage** — its single test is `@pytest.mark.skip` and, even unskipped, catches all exceptions with no asserts.
- **`test_integration_nfc_workflow.py:127-132`** — `main()` discards the boolean results of its three test functions and prints "✓ All integration tests passed!" even when they fail.
- **Silent-pass pattern** — `except ImportError: pass` at [test_property_mode_routing.py:152-155](test_property_mode_routing.py#L152-L155), `test_property_runtime_mode_switching.py:172-174, 242-244`, `test_property_async_interface.py:114-117`: an import failure of NfcScan reports green under pytest.
- **Wrong-shape mocks** — [test_property_mode_routing.py:41-49](test_property_mode_routing.py#L41-L49), `test_property_runtime_mode_switching.py:90-94`: mock the USB path to return a bare string although the real contract is `(data, status)`; they pass only because `get_nfc_input` passes the value through.
- **Interface-shape-only tests** — `test_scanner_error_dialogs.py` (hasattr/signature/docstring checks only), `test_property_async_interface.py`, parts of `test_nfc_scan_routing.py` and `test_integration_nfc_workflow.py` (assert a function is async and its parameter name).
- **Tautology** — [test_scanner_status_messages.py:135-143](test_scanner_status_messages.py#L135-L143) asserts membership in a list defined the line above.
- **Defeated pytest guard** — [test_rental_workflow_integration.py:14-17](test_rental_workflow_integration.py#L14-L17): the `pytest = None` fallback is dead because a module-level `@pytest.mark.asyncio` (line 349) raises `AttributeError` at import when pytest is absent.
- **Hardware-dependent flakiness** — `test_property_device_enumeration.py:123-131` asserts two consecutive hidapi enumerations are identical (flaky if a device flaps); its "property" parameter `iteration` is unused, so the same check runs 100×.
- **Heavy duplication** — mode set/get/persistence is re-tested in ≥6 files; the async-signature check is copy-pasted into 4. Consolidation would also shrink the live-config write surface (C4).

---

## 4. Info & observations

- **Dead code:** `get_card_uid()` (legacy pyscard NFC path, [NfcScan.py:192-225](NfcScan.py#L192-L225)) has no callers but keeps `smartcard` as a hard runtime import (and leaks the card connection on error); `scanning_active` global ([NfcScan.py:23](NfcScan.py#L23)) never used; dataclasses `USBDeviceInfo`/`ScanResult` ([usb_hid_scanner.py:22-39](usb_hid_scanner.py#L22-L39)) and `ScannerConfig` ([scanner_config.py:77-118](scanner_config.py#L77-L118)) never referenced.
- **API currency:** no `datetime.utcnow()` anywhere (all `datetime.now()`, consistent); `declarative_base` imported from the correct SQLAlchemy 2.0 location; the legacy `db.query()` style is still fully supported in 2.x — no deprecation pressure. No deprecated NiceGUI calls found. `Image.NEAREST` still valid in Pillow 12.
- **Environment drift:** the venv is Python 3.11.9, but committed `__pycache__` files are `cpython-313` — the app is evidently also run with a system Python 3.13 outside the venv.
- **`duration_utils.py`** logic is correct, but the docstring example is wrong (95730 s is `1:02:35`, not `2:15:30`), the `D:HH:MM` format is easily misread as `H:MM:SS`, and `format_duration_from_seconds` would raise `OverflowError` on `float('inf')` (currently uncalled).
- **`MatrixCode.py`** builds a new engine per call and never disposes it (harmless with SQLite); unlike most of crud.py it rolls back correctly. It regenerates codes for soft-deleted rows too — safe (id-prefixed) and arguably desirable.
- **Duplication debt:** the five report dialogs duplicate the date-filter + CSV-export block (~80 lines each); `scan_nfc` exists in five diverged variants; the two edit dialogs (`gui_changeUser` vs `gui_changeEquip`) have diverged on None-checks and validation behavior — fixes must currently be applied in many places.
- **CLAUDE.md inaccuracies:** claims the venvs are committed (they are not — `git ls-files` returns 0 files for `bnrs/`/`bnrs_old/`); CLAUDE.md itself is untracked.
- **Unused venv bloat:** `auto-py-to-exe` + its chain (Eel, bottle, gevent) installed but unused; pip 24.0 and setuptools 65.5.0 are old.

### Checked and found OK (no action needed)

- Keyboard vs USB return-type mismatch is correctly adapted in `get_nfc_input`; all callers unpack the tuple correctly.
- `crud.return_equipment` is idempotent — double-clicks can't double-close a rental.
- The manual-select vs background-scan race in `get_user_input_with_selection` is safe (the guard is re-checked with no intervening awaits).
- Late-binding closures are handled correctly throughout the UI (`lambda x=x` defaults, handler factories).
- `gui_changeRental`'s `CLEAR_FIELD` marker round-trips correctly, and rental re-activation is conflict-guarded in `crud.update_rental`.
- Date strings `%Y-%m-%d %H:%M` sort correctly as text; date-range filter logic is consistent across reports.
- No secrets beyond the two known hardcoded ones; no remaining stale references to port 8081 in tracked files.

---

## 5. Recommended fix order

1. **Make the test suite safe** (C3, C4): temp-DB fixture + the `CONFIG_FILE` redirection pattern from `test_property_gui_config_persistence.py`. Until then, don't run bare `pytest` on this machine.
2. **Fix the scan-dialog lifecycle** (C1, C2, M17, and the `.done()` guards): persistent dialogs or hide-handlers that resolve futures; move retry dialogs inside the scan loop; resolve `closed` exactly once; check `cancelled` after the executor read.
3. **Harden the data layer** (M3, M4, M5, M7): rollback-on-failure around commits, WAL + busy_timeout + FK pragmas, duplicate checks that include inactive rows, an already-rented guard in `create_rental` (plus a partial unique index).
4. **Fix the wrong-data UI bugs** (M8, M9, M11, M12, M13, M6): stale selected user, name-only matching in the rental editor, stale lists, duration sorting, stale history session, deactivating rented equipment.
5. **Fix packaging & repo state** (M20, M21, M22, M23, M2, M15): commit `web_viewer/` + the 2.1.4 spec + CLAUDE.md, untrack runtime artifacts (after arranging a DB backup), anchor DB/config/log paths to the app directory, complete requirements.txt.
6. Then work through the Minor list — many are one-line fixes (serialnum default, dead validations, false-success toasts, config merge, atomic save).
