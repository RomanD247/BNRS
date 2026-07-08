# WenglorMEL Rental System — Remediation Plan

**Source:** `CODE_REVIEW_REPORT.md`, whose findings were re-verified line-by-line against current source.
**Branch:** `usb_scan` (all line anchors below are the *current* verified numbers on this branch).
**Ordering:** Steps are ordered by risk and dependency. The single highest-leverage fixes (test isolation, the scan-dialog future contract, and the DB rollback/path-anchoring helpers) come first because most other fixes depend on them. Within each step, every finding is a self-contained task with a checkbox.

There are **79 verified finding entries across 7 review areas**, resolving to **74 unique finding IDs** (5 IDs — `M2`, `M3`, `M7`, `M13`, `tkinter-tk-in-worker-threads` — were reported from two areas each and are handled once, with both angles noted). The Coverage Table at the end maps every ID to its Step.

---

## Ground rules for the executing agent (hard constraints)

1. **Branch & commits.** Work on `usb_scan` (or a dedicated `fix/*` branch cut from it). Commit after **each Step** (or each cohesive task group) with a clear message ending in the required `Co-Authored-By:` trailer. **Never `git commit --amend`** and never force-push.
2. **DO NOT run bare `pytest` on this machine until Step 1 is complete.** The current suite writes to the live `rental.db` and rewrites the live `scanner_config.json` (findings C3/C4). `git status` already shows `M rental.db` and `M logs/scanner.log` as proof. Until isolation fixtures land, run individual non-writing checks only, or run tests against a throwaway copy.
3. **Back up `rental.db` AND `scanner_config.json`** to a safe location before any DB, config, or packaging work. The committed `rental.db` is currently the *only* backup mechanism, and the working copy differs from the committed copy (it shows `M`), so the working copy is authoritative live data.
4. **No migration framework exists.** `Base.metadata.create_all` only adds *missing tables*, never columns or indexes. Any schema change (a new column, a partial unique index, a column-default change) must be applied to the committed `rental.db` **manually via a one-off SQL script** and documented in the commit message. Test the migration on the backup copy first.
5. **Verify each fix by driving the real flow**, not by trusting tests alone. Use the `run` and `verify` skills to launch the native app and exercise the affected path. Each task has a `Verify:` line — run it.
6. **Shared root-cause first.** Several findings collapse onto one fix. Implement the shared helper once, then update call sites:
   - **Path anchoring (M2)** — one `APP_DIR` helper in `database.py`, reused everywhere.
   - **Rollback-on-commit helper `_commit(db)` (M4)** — one helper in `crud.py`, then replace 19 bare commits.
   - **Duplicate-check-including-inactive helpers (M3)** — four `crud.py` getters, reused by crud + all GUI dialogs.
   - **The scan-dialog future-resolution contract (C1/C2/M17 + guards)** — one `_resolve()` helper + persistent dialogs, applied across `get_usb_hid_input`.
   Do not re-solve these per call site.

---

## Step 0 — Preconditions & safety ✅ COMPLETED (2026-07-08)

- [x] **Cut/confirm branch.** Ensure you are on `usb_scan` or a fix branch from it: `git switch usb_scan` (or `git switch -c fix/code-review usb_scan`).
- [x] **Back up live data.** Copy `rental.db` and `scanner_config.json` outside the repo (e.g. to the scratchpad). Record their SHA/size so you can prove they were untouched after Step 1.
- [x] **Note the schema-change policy.** Two later tasks require manual DB migration against `rental.db`: **M7** (partial unique index on open rentals) and, if adopted, **serialnum-default-false**/**tz-naive-timestamps** data cleanups. Prepare a `migrations/` folder or a one-off `.sql`/`.py` script for each; run it on the backup first, then the live DB, and document it.
- [x] **Confirm the venv.** Activate `bnrs/` (`bnrs\Scripts\activate`). `bnrs_old/` is stale — ignore it.

### Review — how Step 0 was done

- **Branch:** already on `usb_scan` (the plan's default target) — no new branch cut, matching the plan's "or" option since this is the branch the review was written against.
- **Venv:** confirmed `bnrs/Scripts/python.exe` reports `Python 3.11.9`, matching CLAUDE.md's documented environment. `bnrs_old/` left untouched.
- **Backups:** `rental.db` and `scanner_config.json` copied to the session scratchpad (outside the repo, not committed — they're live data, not source) with SHA-256 checksums recorded in `BACKUP_MANIFEST.txt` alongside them:
  - `rental.db` — `1c05f6ed1999e3556cfe2ac8ea61fc66f6473d3033ae9f77520298097a6eb9f6`
  - `scanner_config.json` — `8c58556477b917d7a7f84c6f6f7ec18e5c9119dd27629229dedbc1ea0e6658dc`
- **Migration scaffold:** added `migrations/README.md` documenting the manual-migration policy and a tracking table for the three schema-touching changes the later steps call for (M7's partial unique index — required; the two optional/deferred cleanups from Step 7).
- **Note on the working tree:** the repo already had ~72 pre-existing uncommitted changes (deleted `.kiro/specs/*` and root-level `*_SUMMARY.md` docs, modified `main.py`/`NfcScan.py`/several test files/`rental.db`/`requirements.txt`, plus untracked `.hypothesis/` artifacts) from work done before this plan started. None of that was touched, staged, or committed — only this plan file and the new `migrations/README.md` were staged for this step's commit.

---

## Step 1 — Make the test suite safe (do this before running any test) ✅ COMPLETED (2026-07-08)

Two systemic root causes: tests import the production `database.SessionLocal` (bound to `sqlite:///rental.db`) and write to it (C3), and tests call `scanner_config.set_scanner_mode`/`update_usb_config` which rewrite the real `scanner_config.json` (C4). The correct isolation pattern already exists in `test_property_gui_config_persistence.py`. Fix these two first; the test Minors depend on them.

### Reusable snippet A — temp-DB pytest fixture (put in a new repo-root `conftest.py`)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Department, Etype, User, Equipment, Rental
import datetime

@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test_rental.db"
    engine = create_engine(f"sqlite:///{db_file}", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        dep = Department(name="TestDep");  session.add(dep); session.flush()
        et  = Etype(name="TestType");      session.add(et);  session.flush()
        user  = User(name="TestUser", id_dep=dep.id_dep, nfc="1_testuser_1", status=True)
        equip = Equipment(name="TestEquip", serialnum="SN1", etype_id=et.id_et,
                          nfc="1_testequip_sn1", status=True)   # pass serialnum explicitly (models.py:14 default=False bug)
        session.add_all([user, equip]); session.commit()
        yield session
    finally:
        session.close(); engine.dispose()
```

### Reusable snippet B — CONFIG_FILE temp-dir redirect (autouse fixture, same `conftest.py`)

```python
import scanner_config, tempfile, shutil, os

@pytest.fixture(autouse=True)
def isolated_scanner_config():
    original = scanner_config.CONFIG_FILE
    tmp = tempfile.mkdtemp()
    scanner_config.CONFIG_FILE = os.path.join(tmp, "test_scanner_config.json")  # reassign the module attr
    try:
        yield
    finally:
        scanner_config.CONFIG_FILE = original
        shutil.rmtree(tmp, ignore_errors=True)
```
> This works only because `scanner_config` reads the module-global `CONFIG_FILE` at call time (verified at `scanner_config.py:130` and `:185`). New tests must use attribute access `scanner_config.CONFIG_FILE`, never `from scanner_config import CONFIG_FILE`.

---

- [x] **C4 — Multiple tests rewrite the live `scanner_config.json`**
  Files: `scanner_config.py:23,130,185`; `test_integration_nfc_workflow.py:83,95`; `test_rental_workflow_integration.py:355,367`; `test_nfc_scan_routing.py:38,71`; `test_property_mode_routing.py:235`; `test_property_runtime_mode_switching.py:137`; `test_property_async_interface.py:86`; reference pattern in `test_property_gui_config_persistence.py:22,26,38`.
  Now: tests call `set_scanner_mode`/`update_usb_config` (and one writes `Path("scanner_config.json")` directly) against the real file; a keyboard-mode install gets silently flipped and hypothesis tests hammer the live file up to 100×.
  Fix:
  1. Add the **autouse `isolated_scanner_config` fixture** (snippet B) to the new `conftest.py`.
  2. In `test_property_mode_routing.py:235`, change the hardcoded `config_path = Path("scanner_config.json")` to `config_path = Path(scanner_config.CONFIG_FILE)` (add `import scanner_config`) so it hits the redirected temp file. Audit all test files for any other direct `open(...scanner_config.json...)` and do the same.
  3. Remove the hardcoded `set_scanner_mode("usb_vendor")` "restores" at `test_integration_nfc_workflow.py:95` and `test_rental_workflow_integration.py:367` — harmless once redirected, but they encode a wrong assumption.
  4. Add `try/finally` around mode changes in `test_nfc_scan_routing.py` `test_mode_switching` (38-68) and `test_configuration_persistence` (71-93) for uniformity.
  5. For each file's `if __name__ == "__main__"` runner (fixtures don't apply there): either delete the runner (standardize on pytest) or wrap its body in `setup_test_config`/`teardown_test_config` copied from the reference file.
  Verify: rename the real `scanner_config.json`, run the listed test files under pytest, confirm the real file is untouched and `git status` shows no `M scanner_config.json`. Assert inside a test that `scanner_config.CONFIG_FILE` points into a temp dir during the run.

- [x] **C3 — Test suite mutates the live committed `rental.db`**
  Files: `test_rental_workflow_integration.py:30,49,243,273,304,310`; `database.py:6,12`; `crud.py:209,237`.
  Now: tests open `SessionLocal()` bound to `rental.db`; two methods create a real rental (left in history forever) and return a *real* open rental with no restoration.
  Fix:
  1. Add the **`db_session` fixture** (snippet A) to `conftest.py`.
  2. Refactor every test method in `test_rental_workflow_integration.py` (methods at 45, 96, 150, 208, 279, 370) to take `db_session` and drop the `db = SessionLocal()` / `try…finally db.close()` scaffolding (simplest: add `db = db_session` as first line).
  3. Remove the `from database import SessionLocal` import at line 30.
  4. Seed an open `Rental` in the fixture if `test_equipment_lists_after_return` must actually run (else its skip guard trips on the empty temp DB).
  5. Fix the script runner: in `run_all_tests()` (441) and `__main__` (488) either delete it or build a temp engine/session the same way and pass it in. Leave no reachable `SessionLocal()` in the file.
  Verify: `pytest test_rental_workflow_integration.py -v`, then `git status` must NOT list `rental.db`. Temporarily rename `rental.db` and confirm the suite still passes (proves it uses `tmp_path`).
  Depends on: C4 (share the same `conftest.py`).

- [x] **test-defeated-pytest-guard — `pytest = None` fallback dies at a module-level decorator**
  Files: `test_rental_workflow_integration.py:14,349,60`.
  Now: `@pytest.mark.asyncio` at line 349 raises `AttributeError` at import if `pytest` is None, so the fallback is dead code.
  Fix: replace the `try/except ImportError: pytest = None` (14-17) with a plain `import pytest` (pytest is a real project dep). If a pytest-less import must survive, don't use a module-level marker — apply it conditionally after the class.
  Verify: in a venv without pytest, `python -c "import test_rental_workflow_integration"` fails with a clear `ImportError`, not `AttributeError`.
  Depends on: C3.

- [x] **test-background-scanner-zero-coverage**
  Files: `test_background_scanner.py:23,24,28,59`.
  Now: single test is `@pytest.mark.skip`, has no asserts, swallows all exceptions, opens live `SessionLocal()`.
  Fix: it exercises UI-only `get_user_input_with_selection` — rename the file to a non-`test_` name (e.g. `manual_check_background_scanner.py`) and move the `__main__` instructions to docs, OR convert to a real unit test that mocks `get_nfc_input`/the dialog, removes the `except Exception` swallow, uses the `db_session` fixture, and adds asserts.
  Verify: `pytest test_background_scanner.py -v` shows either not-collected or a genuinely asserting test — not `1 skipped`.
  Depends on: C3.

- [x] **test-integration-main-always-passes**
  Files: `test_integration_nfc_workflow.py:129,135,140,49`.
  Now: `main()` discards the four functions' bool returns and unconditionally prints "passed".
  Fix: `results = [test_imports(), test_function_compatibility(), test_rental_workflow_integration(), test_mode_routing_logic()]`; gate the success message on `all(results)`, else print which failed and `return False`. Better: convert to real pytest functions and make ImportError branches `pytest.fail(...)`.
  Verify: rename `NfcScan.py`, run the script — it must fail/exit non-zero.
  Depends on: C4.

- [x] **test-silent-pass-on-importerror**
  Files: `test_property_mode_routing.py:152,211`; `test_property_runtime_mode_switching.py:172,242`; `test_property_async_interface.py:114,146`.
  Now: `try/except ImportError: pass` around the body makes an import failure of `NfcScan` report green.
  Fix: remove the guards; move `from NfcScan import get_nfc_input` to module top. If an optional-dep skip is truly wanted, use `pytest.importorskip("NfcScan")` — never silent `pass`.
  Verify: rename `NfcScan.py`, run — results show errors/skips, never "passed".
  Depends on: C4.

- [x] **test-wrong-shape-mocks — USB mocks return a bare string instead of `(data, status)`**
  Files: `test_property_mode_routing.py:41,292`; `test_property_runtime_mode_switching.py:90,334,209`.
  Now: usb-path mocks set `return_value = "..."` and assert equality; passes only because `get_nfc_input` passes the USB return through untouched.
  Fix: make usb mocks return the tuple `("...", "success")` and unpack in the assertion (`data, status = ...; assert data == ...`). Delete the dead line at `:209`. Leave keyboard-mode mocks as bare strings (they test the string→tuple wrapping).
  Verify: temporarily double-wrap the tuple in `get_nfc_input`'s usb branch and confirm these tests now fail.
  Depends on: C4.

- [x] **test-tautology-status-values**
  Files: `test_scanner_status_messages.py:135,137,140`.
  Now: builds `valid_statuses` then asserts those same literals are in it — cannot fail.
  Fix: delete it, or define a canonical status set in production (`NfcScan`/`scanner_config`), import it, and assert returned statuses are members of it.
  Verify: change a source-of-truth status and confirm the test fails.

- [x] **test-interface-shape-only — introspection-only tests, duplicated**
  Files: `test_scanner_error_dialogs.py:17,69,123`; `test_property_async_interface.py:31`; `test_nfc_scan_routing.py:106`; `test_integration_nfc_workflow.py:24`.
  Now: many tests only check `hasattr`/`iscoroutinefunction`/signature/docstring substrings.
  Fix: keep ONE async-signature smoke test (in `test_property_async_interface.py`); delete the duplicates in `test_nfc_scan_routing.py` (96-121) and `test_integration_nfc_workflow.py` (16-49). Replace the docstring-substring assertion at `test_scanner_error_dialogs.py:123` with a behavioral test (patch `hid` to raise permission error; assert `connect` behavior) or delete it. Add at least one dialog-behavior assertion.
  Verify: grep shows `iscoroutinefunction`/`inspect.signature` in exactly one place; error-dialog file has ≥1 behavioral assertion.

- [x] **test-device-enumeration-flakiness**
  Files: `test_property_device_enumeration.py:65,67,123,129`.
  Now: `iteration` param unused (100 identical no-ops); two independent live `hid.enumerate()` snapshots compared → racy/hardware-dependent.
  Fix: drop the property or use `iteration` meaningfully; **mock `usb_hid_scanner.hid.enumerate`** with a fixed device list and assert `list_devices()` reflects it; derive both sides from ONE enumeration; add `pytest.importorskip("hid")`/`skipif` and convert empty-list early-returns to `pytest.skip`.
  Verify: with `hid` mocked, run repeatedly — zero flakiness; the consistency test no longer runs 100 no-op iterations.

- [x] **test-heavy-duplication**
  Files: `test_nfc_scan_routing.py:38`; `test_integration_nfc_workflow.py:78`; `test_property_mode_routing.py:18`; `test_property_runtime_mode_switching.py:19`; `test_property_async_interface.py:151`; `test_property_gui_config_persistence.py:96`.
  Now: mode set/get/persistence and the async-signature check are re-implemented in 6+ files, each writing the live config.
  Fix: with `conftest.py` in place, consolidate mode set/get/persistence into ONE parametrized test (`@pytest.mark.parametrize` over `['usb_vendor','keyboard']`) plus the hypothesis versions kept in `test_property_mode_routing.py`; delete redundant copies; consolidate the async-signature check into one location. All remaining tests run under the autouse isolation fixture.
  Verify: grep for `set_scanner_mode(` / `iscoroutinefunction` collapses to the consolidated spots; full `pytest` passes with `git status` clean.
  Depends on: C4.
  **Resolution:** the `iscoroutinefunction`/interface-shape half was fully consolidated by the `test-interface-shape-only` fix above (verified by grep — `get_nfc_input`'s signature check now lives only in `test_property_async_interface.py`; the remaining two occurrences check different functions, `nfc_equipment_rental_workflow` and `get_usb_hid_input`). For the "mode set/get/persistence re-implemented in 6+ files" half: read the actual body of every `*persistence*`/`*mode*` test across `test_nfc_scan_routing.py`, `test_property_mode_routing.py`, `test_property_runtime_mode_switching.py`, and `test_property_gui_config_persistence.py` before consolidating, and found they are **not** literal duplicates — each exercises a distinct angle (basic mode detection vs. routing-dispatch-to-the-right-backend vs. disk-reload-after-switch vs. GUI-write-path JSON structure vs. call-to-call routing freshness vs. property-fuzzed round trips). Deleting any of them on "looks similar" grounds risked silently dropping real coverage for a cosmetic win, so no tests were deleted here — this is a considered judgment call, not an oversight. All of them now run under the autouse `isolated_scanner_config` fixture regardless, so the original safety concern (live file writes) is fully closed either way.

**Commit Step 1** (e.g. "Isolate test suite: temp DB + config redirect fixtures").

### Review — how Step 1 was done

**conftest.py (new, repo root)** — the shared fixture file with `db_session` (throwaway per-test SQLite DB in `tmp_path`, seeded with a Department/Etype, a `TestUser`/`TestEquip` pair, and a second `TestEquipRented` unit with an already-open rental so return-flow tests don't have to skip) and the autouse `isolated_scanner_config` (redirects `scanner_config.CONFIG_FILE` to a fresh temp path per test, restores it after).

**C3 (critical, done directly, not delegated)** — `test_rental_workflow_integration.py` rewritten: all 6 test methods now take `db_session` instead of opening the live `SessionLocal()`; the dead `run_all_tests()`/`__main__` script runner (which could never work with a fixture-based session) was deleted, standardizing on pytest. Verified: 7/7 tests pass in isolation; SHA-256 of the live `rental.db` and `scanner_config.json` confirmed byte-identical to the pre-Step-1 backup both immediately after and again after the full 54-test suite run.

**C4 + 8 test-quality Minors (delegated to 9 parallel agents, one per file, then independently verified)** — each agent fixed only its assigned file/findings and self-verified with a scoped `pytest <file> -v` run:
- `test_property_mode_routing.py` — hardcoded `Path("scanner_config.json")` → `Path(scanner_config.CONFIG_FILE)`; removed silent `except ImportError: pass` guards; fixed two USB-mode mocks to return `(data, status)` tuples.
- `test_integration_nfc_workflow.py` — deleted the duplicate interface-shape test; removed the wrong-assumption `set_scanner_mode("usb_vendor")` restore; `main()` now gates its success message on `all(results)` instead of always printing "passed".
- `test_nfc_scan_routing.py` — added `try/finally` mode restoration to two tests; deleted the duplicate interface-shape test (and its now-dangling call in `main()`).
- `test_property_runtime_mode_switching.py` — confirmed no hardcoded config path existed (already compliant); removed 4 silent-ImportError guards (2 more than the plan's literal line list — the agent found the same anti-pattern twice more in the same file and fixed all 4 for consistency); fixed 3 wrong-shape mocks, including deleting one now-dead overwritten line.
- `test_property_async_interface.py` — confirmed C4-compliant already; removed all 4 silent-ImportError guards in the file (again, 2 more than the literal cited lines, fixed for the same-file consistency reason); kept this file's `iscoroutinefunction(get_nfc_input)` check as the canonical copy per the plan.
- `test_scanner_status_messages.py` — deleted the tautological `test_status_values` test after confirming no production-code canonical status constant exists to assert against instead (a hand-copied list would just reproduce the same problem one level removed).
- `test_scanner_error_dialogs.py` — replaced the docstring-substring assertion with a real behavioral test: mocks `hid.device.open()` to raise `IOError`, calls the real `USBHIDScanner.connect()`, asserts it raises `PermissionError` and resets state correctly.
- `test_property_device_enumeration.py` — dropped the unused-parameter hypothesis wrapper; mocked `usb_hid_scanner.hid.enumerate` with one fixed device list shared by all comparisons (previously two independent live hardware calls were compared against each other); added `pytest.importorskip("hid")`; converted silent early-returns to `pytest.skip(...)`. Confirmed deterministic across repeated runs.
- `test_background_scanner.py` → renamed to `manual_check_background_scanner.py` (via `git mv`, confirmed as a tracked rename): the single test drove a live NiceGUI dialog with no headless-testable behavior, so per the finding's own guidance it's now clearly documented as a manual/interactive check rather than a fake automated test; `@pytest.mark.skip`, the `except Exception: pass` swallow, and the live `SessionLocal()`-as-a-"test" framing were all removed.

**Independent verification (by me, not the agents' self-reports):** re-read every agent's diff; ran all touched files together (50 passed) and then the **entire suite** (`pytest` with no path argument — the first time this was safe to do per the plan's ground rules) — **54 passed, 0 failed**. Confirmed via SHA-256 that `rental.db` and `scanner_config.json` are still byte-identical to the Step 0 backup after the full run; `git status` shows no new modification to either beyond the pre-existing drift noted in Step 0.

**Not fixed / explicitly out of scope:** the pre-existing `PytestReturnNotNoneWarning`s (many tests `return True`/`False` instead of using bare `assert`) surfaced across the suite — these predate this session, aren't part of any Step 1 finding, and were left untouched by every agent to avoid scope creep.

---

## Step 2 — Scan-dialog lifecycle & scanner control flow

C1, C2, M17, the `.done()` guards, the cancel race, and the two error-dialog Minors all converge on **one root defect** in `get_usb_hid_input`: an `asyncio.Future` (`closed`) resolved in multiple unguarded places, plus background tasks (`scan_task`, `usb_scanner_background_task`, `maintain_focus`) that outlive dialog dismissal. Implement the shared contract first, then apply per-finding deltas. All line numbers are in `NfcScan.py` unless noted.

### Target future-resolution contract (implement once)
1. Immediately after `closed = asyncio.Future()` (line 248) add:
   ```python
   def _resolve():
       if not closed.done():
           closed.set_result(None)
   ```
2. Replace **every** `closed.set_result(None)` in `get_usb_hid_input` with `_resolve()` (current occurrences: 259, 314, 333, 395, 403, 419, 436, 452).
3. Retry-capable error dialogs are awaited **inside the loop without resolving `closed` first**. `_resolve()` + `return` only on terminal outcomes (cancel/fallback/max-retries).
4. Make dialogs **persistent** so ESC/outside-click cannot orphan the future.
5. Guard **all** other `set_result` calls in the file with `if not <future>.done():`.

- [ ] **C1 — USB retry flow resolves `closed` too early and can double-resolve it**
  Files: `NfcScan.py:248, 252-259, 290-297, 306-363, 384-396, 397-459, 461-472, 475-480`.
  Now: six error paths resolve `closed` *before* awaiting their retry dialog, so `await closed` (478) returns while `scan_task` still runs; a later success then hits `set_result` on a resolved future → `InvalidStateError`, caught and re-raised again → unhandled task exception. Retried scans have no visible dialog.
  Fix:
  1. Add the `_resolve()` helper (contract step 1) and swap all resolutions (step 2).
  2. For each retry-capable branch (permission 306-323, connect-failure 325-363, disconnect 397-412, timeout 413-428, corrupted 430-445): **remove the premature resolution**, keep `dialog.close()`, then after the error dialog returns `if choice == 'retry': retry_count += 1; continue` and **re-show the scanning dialog** at the top of the loop; call `_resolve()` + `return` only on terminal choices.
  3. Success path (384-396): add `if cancelled: return` before the `if scan_data:` block (see M17); keep a single guarded `_resolve()`.
  4. Generic `except Exception` (447-459): one guarded `_resolve()` then `return`.
  5. `on_cancel` (259): use `_resolve()`.
  6. After the loop (466-472): call `_resolve()` so the caller always unblocks.
  7. Ensure the scanning dialog is visible during retries (re-open at loop top, or don't `dialog.close()` in retry branches) — pick one and be consistent.
  Verify: set wrong VID/PID → connection-error dialog appears *before* any "Scanner not connected" toast; Retry with a reachable device → exactly one rental workflow, no `InvalidStateError`; Retry to max → caller unblocks with the max-retries notification.
  Depends on: C2, M17, missing-done-guards-nfcscan.

- [ ] **C2 — Scan/confirm dialogs are not persistent; ESC leaves futures unresolved and leaks loops/HID handle**
  Files: `NfcScan.py:247, 496, 536-542, 601, 612-616, 738, 1053, 1103`.
  Now: no dialog uses `.props('persistent')`; ESC runs no handler → keyboard `maintain_focus` loops forever (focus stolen), USB background loop holds the HID device until restart, confirm/return workflows await forever.
  Fix (Option A, recommended — mirror the admin dialog at `main.py:573`): change each `ui.dialog()` to `ui.dialog().props('persistent')` at lines 247, 496, 601, 1053, 1103. Users must exit via the explicit buttons that already resolve the futures. (Option B if dismissal must stay: add `dialog.on('hide', …)` handlers that resolve the future as cancelled, guarded with `.done()`, and for `get_usb_hid_input` also set `cancelled=True` to stop `scan_task`.)
  Verify: for each dialog press ESC / click outside — it must not close. In keyboard mode, confirm focus is not stolen. In usb_vendor mode, ESC the Select-User dialog then immediately start another scan — the scanner reconnects (handle released).
  Depends on: C1, M17, missing-done-guards-nfcscan.

- [ ] **M17 — Cancel race: blocking HID read keeps running after Cancel; `cancelled` not re-checked**
  Files: `NfcScan.py:252-259, 381-382, 384-396, 461-464`.
  Now: `on_cancel` resolves `closed`, but `scan_task` may still be blocked in `run_in_executor(scanner.read_scan)`; when it returns, the success branch runs with no `cancelled` re-check → same `InvalidStateError` cascade; device held for up to `timeout`.
  Fix:
  1. Immediately after the executor read (382) insert `if cancelled: return` (before `if scan_data:` at 384). With C1's guarded `_resolve()` this fully prevents the crash.
  2. (Optional, releases device sooner) add a `self._cancel` flag + `scanner.cancel()` to `USBHIDScanner`, checked each iteration of `read_scan`'s loop (`usb_hid_scanner.py:168-194`), and call it from `on_cancel`.
  Verify: usb_vendor mode — start scan, Cancel, then scan a valid code within the timeout: nothing happens, no `InvalidStateError`. Dialog reopens immediately if the optional flag is added.
  Depends on: C1.

- [ ] **missing-done-guards-nfcscan — future resolutions lack `.done()` guards**
  Files: `NfcScan.py:1056-1067, 1108-1114, 259, 504, 508, 616, 623, 643, 754`.
  Now: rapid double-click (or an ESC hide handler racing a button) double-resolves → `InvalidStateError`.
  Fix: guard every `<future>.set_result(...)` with `if not <future>.done():`. For the return dialog `on_confirm` (1056-1063), guard the **whole body** with `if confirmed.done(): return` at the top so `crud.return_equipment`/`update_callback`/toast don't fire twice. For `get_usb_hid_input` use the shared `_resolve()`.
  Verify: double-click "Confirm Return" and "Confirm Rental" — no `InvalidStateError`, exactly one toast, one `update_callback`.
  (Prerequisite for C2 Option B.)

- [ ] **disconnect-during-executor-read — `disconnect()` can run while the executor thread is inside `read_scan`**
  Files: `NfcScan.py:796-807, 738-742, 775-778`; `usb_hid_scanner.py:129-138`.
  Now: cleanup does `scanner_task.cancel()` then the task's `finally` calls `scanner.disconnect()` (`device.close()`) while the executor thread may still be in `device.read()` — hidapi concurrent close+read is unsafe.
  Fix: don't `cancel()`. Set `scanner_cancelled = True`, then `if scanner_task is not None: await scanner_task` (no cancel). The loop condition (`while not scanner_cancelled and not result.done():`, 738) + the 2 s read timeout let the read finish, the loop exit, and `finally: disconnect()` run only after `read_scan` returns. Optionally bound with `asyncio.wait_for(..., timeout=slightly_over_read)`.
  Verify: rapidly confirm/cancel the Select-User dialog while the background scanner polls; no hidapi errors; log shows "Background scanner disconnected" *after* the last read.

- [ ] **retry-counter-double-increment — connection-retry counter increments twice**
  Files: `NfcScan.py:336-338, 347-356`; `scanner_error_dialogs.py:119, 127-128`.
  Now: `retry_connection` increments `retry_count` (338) *and* the caller increments again (354) — each Retry advances by 2, so ~2 real attempts of 3.
  Fix: empty `retry_connection`'s body — change lines 337-338 to `pass` (keep the `async def` stub so the "Retry Connection" button still renders; it is gated on truthy `retry_callback` at `scanner_error_dialogs.py:119`). Keep the single authoritative `retry_count += 1` at line 354. Do **not** set `retry_callback=None`.
  Verify: wrong VID/PID, click Retry 3× → three connection attempts before "Maximum retry attempts reached".
  Depends on: C1.

- [ ] **contradictory-keyboard-fallback-ux — fallback shows both a "not connected" and a "switched" toast and doesn't restart the scan**
  Files: `NfcScan.py:329, 332-333, 340-345, 357-359, 1035-1036`.
  Now: connect-failure pre-resolves `closed` (caller shows "Scanner not connected"), and the fallback also toasts "Switched to keyboard mode. Please restart the scan." — two contradictory messages, no auto-restart.
  Fix (fold into C1's restructure): on `choice == 'fallback'`, after `set_scanner_mode('keyboard')`, **restart the scan in keyboard mode**: `data, st = await get_nfc_input_keyboard(prompt_message); result = data; status = 'cancelled' if not data else 'success'; _resolve(); return`. If auto-restart is undesired, at minimum set `status='cancelled'` before resolving so the caller (1033-1038) doesn't print "Scanner not connected", and reduce the notification to one clear message. Stop relying on the pre-set `status='not_connected'` (329) for the fallback path.
  Verify: usb_vendor mode, disconnected scanner, click "Use Keyboard Mode" → exactly one coherent outcome; `scanner_config.json` shows `keyboard`.
  Depends on: C1.

- [ ] **error-dialogs-retry-double-increment-and-done-guards (scanner_error_dialogs.py)**
  Files: `scanner_error_dialogs.py:56-69, 152-160, 206-214, 260-268, 326-334, 124-130`; `NfcScan.py:336-338, 353-354`.
  Now: (1) same double-increment as above (fixed in `NfcScan.py`); (2) every dialog's `on_retry/on_cancel/on_fallback` calls `result.set_result(...)` unguarded.
  Fix: add `if not result.done():` before every `result.set_result(X)` in `scanner_error_dialogs.py` (on_retry 59, on_fallback 64, on_cancel 69; timeout 155/160; disconnection 209/214; corrupted 263/268; permission 329/334). The increment half is handled by `retry-counter-double-increment`.
  Verify: unit-test calling `on_retry()` then `on_cancel()` on one dialog future → no `InvalidStateError`, first result wins.
  Depends on: C1, C2, M17.

**Commit Step 2** ("Fix scan-dialog future lifecycle, persistence, cancel race, retry counter").

---

## Step 3 — Harden the data layer

Do the **shared roots first**: M2 (path anchoring), M4 (rollback helper), M3 (inactive-aware duplicate helpers). M3 + M4 + M7 interact — implement the combined approach below.

- [ ] **M2 — Relative sqlite path + `create_all` on import silently creates an empty DB in the wrong CWD; frozen `__file__` wrong; constant duplicated** *(shared root cause — data-layer + main-app)*
  Files: `database.py:6,9,15`; `main.py:30,33,881,901`; `fill_nfc_fields.py:17,23`; also anchor `scanner_config.py:23` (CONFIG_FILE) and `scanner_logging.py:17` (LOG_DIR).
  Now: `DATABASE_URL = "sqlite:///rental.db"` is CWD-relative; `create_all` runs at import; launching from another dir manufactures an empty DB. No `sys.frozen` handling anywhere. `fill_nfc_fields.py` duplicates the constant.
  Fix (do once in `database.py`, export `APP_DIR`):
  1. Top of `database.py`: `import sys, os` and `from pathlib import Path`. Compute `APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent` **before** line 6 (create_all at 15 runs on import).
  2. Replace line 6 with `DATABASE_URL = "sqlite:///" + (APP_DIR / "rental.db").as_posix()` (forward slashes; SQLAlchemy accepts `sqlite:///C:/…`).
  3. Frozen one-file seed: if the anchored `rental.db` doesn't exist but a bundled copy exists under `sys._MEIPASS`, `shutil.copy` it to `APP_DIR` before `create_all`.
  4. `fill_nfc_fields.py:17`: delete the duplicate constant; `from database import DATABASE_URL` (mirrors `MatrixCode.py`). `MatrixCode.py` already imports it → auto-fixed.
  5. `main.py:881,901`: replace `os.path.dirname(__file__)` with `APP_DIR` (import from `database`) — overlaps M15.
  6. Reuse `APP_DIR` for `scanner_config.CONFIG_FILE` and `scanner_logging.LOG_DIR` (a single `paths.py` or importing from `database` avoids re-duplicating the frozen branch).
  Verify: run `python C:\…\BNRS\main.py` from a *different* CWD and confirm existing equipment/users appear and no new `rental.db` is created in the launch dir. Build the exe, move it to a fresh folder, confirm data persists and no `rental.db` appears in CWD. Run `fill_nfc_fields.py` from another CWD and confirm it edits the real DB.
  Depends on: M4, M5 (batch with them), M15 (main-app viewer paths).

- [ ] **M4 — 19 crud writes commit with no try/rollback → poisoned long-lived sessions** *(linchpin: M2/M3/M5/M6/M7 + update-user-mutates depend on it)*
  Files: `crud.py:12,33,42,51,73,83,91,117,126,139,173,183,196,205,218,242,266,793,830`.
  Now: every write except `update_rental` does a bare `db.commit()`. After any IntegrityError/"database is locked", the long-lived module session sits in a failed transaction → `PendingRollbackError` until restart.
  Fix:
  1. Add near the top of `crud.py`:
     ```python
     def _commit(db):
         try:
             db.commit()
         except Exception:
             db.rollback()
             raise
     ```
  2. Replace every bare `db.commit()` at the listed lines with `_commit(db)`. Leave `db.refresh(...)` calls (they run only on success). Do **not** touch `update_rental` (already guarded, 834-1016).
  3. Callers should catch the re-raised exception and `ui.notify` — audit main/gui callers (coordinate with Step 4), but session-poisoning is fixed once `_commit` is in place.
  Verify: force an IntegrityError (e.g. create_etype twice with the same name after M3), then do an unrelated read/write on the same session — it must succeed (no `PendingRollbackError`).

- [ ] **M3 — Duplicate/unique pre-checks are blind to soft-deleted rows; create_* have no dup check** *(shared root cause — data-layer + gui-dialogs)*
  Files: `models.py:18,25,33,46`; `crud.py:47,61,87,105,168,746,759,824`; GUI call sites `gui/gui_addequip.py:73,28`, `gui/gui_adduser.py:81,42`, `gui/gui_changeUser.py:95`, `gui/gui_changeEquip.py:91,224`.
  Now: pre-checks use status-filtered getters, so a code/name held by a soft-deleted row reads as free → raw `UNIQUE constraint failed` at commit. `create_etype`/`create_department`/`create_user`/`create_equipment` have no dup check at all.
  Fix (helpers once, then call sites):
  1. Add to `crud.py`: `find_user_by_nfc_including_inactive`, `find_equipment_by_nfc_including_inactive`, `get_etype_by_name_including_inactive`, `get_department_by_name_including_inactive` — each the sibling query **without** `.status == True`.
  2. `update_user` (169) and `update_user_nfc` (825): use `find_user_by_nfc_including_inactive` in the dup check; keep the `existing.id != user_id` guard.
  3. `create_etype` (47-53) and `create_department` (87-93): add a pre-check via the `*_including_inactive` name getter; if a row exists, raise a clear `ValueError` ("Name already exists — possibly on a deactivated record") or reactivate it (decide policy — see update-cannot-reactivate).
  4. `create_user` (137) / `create_equipment` (10): if `nfc` provided, pre-check via `find_*_by_nfc_including_inactive` and raise a friendly `ValueError`.
  5. GUI dialogs: swap the four getters to the `*_including_inactive` variants; when the match is an inactive row, show a "belongs to deactivated …" warning. Replace `gui_addequip` `add_etype`'s `if new_et in main_data` and `gui_adduser` `add_department`'s `if new_dep in data` with the inactive-aware name getters. (Note: `gui_adduser`'s scan path is dead code — button commented at 133-136 — fix anyway for when re-enabled.)
  Verify: soft-delete an Etype "Foo", then `create_etype("Foo")` → friendly `ValueError`/reactivation, not IntegrityError. Same for assigning a soft-deleted user's nfc to a live user.
  Depends on: M4 (the still-slipping IntegrityError must roll back cleanly).

- [ ] **M5 — Two processes share one SQLite file with no WAL/busy_timeout/FK enforcement**
  Files: `database.py:9`; `models.py:53,54`.
  Now: `create_engine(DATABASE_URL, echo=True)` with default rollback-journal mode; main app + web viewer contend → "database is locked"; FKs off; nullable rental FKs allow orphans (feeds the NOT-IN NULL bug).
  Fix:
  1. `from sqlalchemy import event`.
  2. After `engine = create_engine(...)`:
     ```python
     @event.listens_for(engine, "connect")
     def _set_sqlite_pragma(dbapi_conn, conn_record):
         cur = dbapi_conn.cursor()
         cur.execute("PRAGMA journal_mode=WAL")
         cur.execute("PRAGMA busy_timeout=5000")
         cur.execute("PRAGMA foreign_keys=ON")
         cur.close()
     ```
  3. **Before enabling `foreign_keys=ON`**, run a one-time check for orphans: `SELECT * FROM rentals WHERE equipment_id NOT IN (SELECT id_eq FROM equipment) OR user_id NOT IN (SELECT id_us FROM users)` and clean up, else inserts start failing.
  4. Add `rental.db-wal` and `rental.db-shm` to `.gitignore` (M22).
  Verify: run the app; `rental.db-wal`/`-shm` appear. Open the viewer concurrently and rent/return — no "database is locked". Insert a rental with a bogus `equipment_id` via script → IntegrityError.
  Depends on: M4. (Batch the edit with `echo-true`, same line.)

- [ ] **M6 — Soft-deleting rented equipment hides its open rental and makes it unreturnable**
  Files: `crud.py:37,199,246,759,761`; `gui/gui_changeEquip.py:218`.
  Now: `delete_equipment` and the Etype bulk toggle flip `status=False` with no rental check; then the open rental disappears from all active-rental queries and `find_equipment_by_nfc`, so it can never be returned.
  Fix:
  1. `delete_equipment` (37-44): before `status=False`, `if is_equipment_rented(db, equipment_id): raise ValueError("Cannot deactivate equipment that is currently rented — return it first")`.
  2. `update_etype_equipment_status` (199-206): when `new_status` is False, query for any active rental in that type and raise/skip (or exclude rented units).
  3. `gui_changeEquip.py:218` (bypasses crud): add the same `is_equipment_rented` guard before flipping status.
  4. Secondary (rescue existing orphans): consider removing `.filter(Equipment.status == True)` from `get_active_rentals` (252), `get_active_rentals_by_equipment_type` (312), `get_active_rentals_summary` (387) so orphaned open rentals stay returnable — confirm with product owner (changes Available/Rented UI semantics).
  Verify: rent an item, try to deactivate via both paths → blocked; return it → deactivation succeeds.
  Depends on: M4.

- [ ] **M7 — No double-rental protection: `create_rental` inserts unconditionally; no DB constraint** *(shared root cause — data-layer + main-app; see also M8/M11)*
  Files: `crud.py:209,218,761`; `models.py:48`; `main.py:151,153`.
  Now: `create_rental` never checks `is_equipment_rented`; the manual rent dialog also doesn't; a double-click / stale list / editor re-open yields two open rentals.
  Fix:
  1. **App-layer guard (protects all callers)** — `create_rental` (209-220): `existing = is_equipment_rented(db, equipment_id); if existing: raise ValueError(f"Equipment is already rented (rental id {existing.id_re})")`.
  2. **Manual dialog guard** — `main.py` `on_confirm` (151): after confirming `state.selected_user`, `existing = is_equipment_rented(db, equipment.id_eq)` (add `is_equipment_rented` to the crud import block 24-29); if truthy, `ui.notify(..., type='warning')`, `dialog.close()`, `refresh_with_filters()`, `return`. Disable the Confirm button on first click to close the TOCTOU window.
  3. **DB partial unique index (race guard)** — `models.py`: `from sqlalchemy import Index` and `Index('uq_active_rental_per_equipment', Rental.equipment_id, unique=True, sqlite_where=(Rental.rental_end.is_(None)))`.
  4. **Manual migration** (create_all won't add it): dedupe existing double-open rentals first, then `CREATE UNIQUE INDEX IF NOT EXISTS uq_active_rental_per_equipment ON rentals(equipment_id) WHERE rental_end IS NULL;` against `rental.db` (run on the backup first; document in the commit). Enforce `equipment_id NOT NULL` (via M5) so multiple NULLs can't slip through.
  Verify: `create_rental` twice for one equipment → second raises `ValueError`; raw INSERT of a second open rental → IntegrityError; `SELECT equipment_id, COUNT(*) FROM rentals WHERE rental_end IS NULL GROUP BY equipment_id HAVING COUNT(*)>1` returns zero rows.
  Depends on: M4, M5; interacts with M8, M11.

**Commit Step 3** ("Harden data layer: path anchoring, rollback helper, dup checks, pragmas, rental guards"). Document the M7 index migration in the message.

---

## Step 4 — Wrong-data UI bugs

- [ ] **M8 — Stale `state.selected_user` can rent to the wrong user**
  Files: `main.py:45,145,151,158`.
  Now: `state.selected_user` cleared only on successful confirm; closing via X/ESC leaves it set → next dialog Confirm (without selecting) rents to the previous user.
  Fix (best): make selection **local to the dialog** — replace `state.selected_user` reads/writes in `show_rent_dialog` with a closure `selected_user_id = None` (`nonlocal` in `on_user_select_modified`/`on_confirm`). Minimal: reset `state.selected_user = None` at the top of `show_rent_dialog` (143). If keeping the global, also clear it on dialog hide (`dialog.on('hide', lambda: setattr(state,'selected_user',None))`) covering the X button (192) and ESC.
  Verify: open dialog for A, select Alice, close via X; open for B, click Confirm without selecting → "Please select a user!", no rental for B.
  Depends on: M7.

- [ ] **M9 — Rental editor resolves user/equipment by display NAME only → wrong unit**
  Files: `gui/gui_changeRental.py:182,190,309,326,328`.
  Now: dropdowns built from non-unique names; save matches by name (equipment even strips the serial back off) → first match wins.
  Fix: build id-lookup dicts. Users: `display = f"{u.name} ({u.department.name}) [#{u.id_us}]"`, `users_by_display[display] = u.id_us`. Equipment: `display = f"{eq.name} (S/N: {eq.serialnum or 'No S/N'}) [#{eq.id_eq}]"`, `equipment_by_display[display] = eq.id_eq`. Set `user_value`/`equipment_value` to the **same** display strings (char-for-char, or NiceGUI shows blank). Pass the dicts into `save_rental_changes`; replace the name-based `next(...)` lookups (309, 326-328) with dict lookups + not-found guards; delete the `split(' (S/N:')` logic.
  Verify: two equipment rows same name/different serial; edit a rental on the second, change only the comment, save, reopen → S/N unchanged and `rentals.equipment_id` unchanged. Repeat with two same-named users.
  Depends on: M10 (same functions — apply together).

- [ ] **M10 — Rental editor cannot save edits when the user/equipment was soft-deleted**
  Files: `gui/gui_changeRental.py:130,131,309,408`; `crud.py:877,892`.
  Now: dropdowns load only active rows, so a rental for a departed user/retired device is edit-locked; even a date/comment change fails.
  Fix: load **including inactive** for the dropdowns/dicts: `crud.get_all_users_including_inactive` (crud.py:186) and `crud.get_all_equipment_including_inactive` (crud.py:592). Capture `original_user_id`/`original_equipment_id` before building the form; in `save_rental_changes` only pass `user_id`/`equipment_id` to `update_rental` when they **changed** (pass `None` otherwise — `update_rental` skips `None`, avoiding the inactive re-validation at crud.py:882-883/897-898). Optionally label inactive entries " (inactive)".
  Verify: soft-delete a rental's user, open the editor, change only the comment, save → succeeds; reopen shows new comment; `rentals.user_id` unchanged. Reassign to a different active user → also succeeds.
  Depends on: M9, M4.

- [ ] **M11 — Newly added equipment doesn't appear when no filter is active**
  Files: `main.py:116,120,129`; `gui/gui_addequip.py:103`; `main.py:597`.
  Now: `update_lists` only re-queries when a filter is set; otherwise it re-renders the stale in-memory list, so a newly added device shows a toast but no card.
  Fix: make `apply_combined_filters()` unconditional — change the guard at `main.py:120-121` to always call it (it already handles the no-filter case, 273-290). Optionally drop the now-duplicate `apply_combined_filters()` in `filter_by_etype` (250) and `on_name_filter_change` (292). (Lower-risk alternative: wire `gui_addequip`'s callback at `main.py:597` to `refresh_with_filters` instead of `update_lists`.)
  Verify: with no filter, Admin → Add Device → new card appears immediately without "Refresh all data". With a type filter set, a new device of that type still appears.

- [ ] **M12 — Duration columns sort lexicographically; history mixes in "Active rental"**
  Files: `gui/gui_reports.py:208,327,449,533,543,550,754`; `crud.py:469,566,654,722`.
  Now: duration is an unpadded `D:HH:MM` string, so `'9:…'` sorts above `'85:…'`; history's Duration column also contains the literal "Active rental".
  Fix:
  1. `crud.py`: add `'total_rental_seconds': int(total_seconds) if total_seconds else 0` to each stats-row dict in `get_user_rental_statistics` (~479), `get_equipment_type_statistics` (~580), `get_equipment_name_statistics` (~665), `get_department_rental_statistics` (~730).
  2. `gui_reports.py`: on each `total_rental_time` column (defined at 141, 264, 386, 691) add a Quasar custom sort key `':sort': '(a, b, rowA, rowB) => (rowA.total_rental_seconds ?? 0) - (rowB.total_rental_seconds ?? 0)'` (keep `field='total_rental_time'` for display).
  3. History: add a numeric `duration_seconds` per row (`int((end-start).total_seconds())`; `None` for active); add `':sort': '(a, b, rowA, rowB) => (rowA.duration_seconds ?? Number.MAX_SAFE_INTEGER) - (rowB.duration_seconds ?? Number.MAX_SAFE_INTEGER)'` to the Duration column (533).
  Do **not** zero-pad the day segment (unbounded). Only `sortable:true` columns use the comparator — all four already are.
  Verify: one user ~9 days, another ~85 days → descending lists the 85-day user first; toggle ascending → 9 first. In history, "Active rental" rows group at one end.

- [ ] **M13 — Reports read through a never-expired module session → returned rentals still show "Not returned"** *(main-app + gui-dialogs; real fix lives in gui_reports)*
  Files: `gui/gui_reports.py:21,540,543,560`; `main.py:346,338`.
  Now: `gui_reports.py:21` holds a module-level `db = SessionLocal()` never expired; `full_refresh` only expires `main.py`'s session, so History stays stale until restart.
  Fix (in `gui_reports.py`): wrap `show_rental_history`'s data load in `with SessionLocal() as fresh_db:` and call `get_all_rentals(fresh_db)`, materializing all needed values into the plain-dict list (552-563) **before** the block closes. Do the same for the other report builders (`show_user_rental_statistics` 149/197, `show_equipment_type_statistics` 272/316, `show_equipment_name_statistics` 394/439, `show_department_rental_statistics` 699/744, `show_feedback_entries` 822). Minimal alternative: `db.expire_all()` at the top of each report function. Optionally drop the module `db` at line 21. `main.py:346` is only evidence — no functional change needed there beyond documenting that "Refresh all data" cannot reach already-open report dialogs.
  Verify: rent then return an item on the main screen, open Admin → Rental History without restart → returned row shows a real `rental_end` and computed duration.

- [ ] **M14 — Edit dialogs change code-bearing fields without regenerating the nfc payload or warning**
  Files: `gui/gui_changeUser.py:211`; `gui/gui_changeEquip.py:215,216,228`; `MatrixCode.py:46,106`.
  Now: renaming a user/device or editing serial/dept leaves the stored `nfc` encoding the OLD values; when "Update codes" is later run it overwrites `nfc`, invalidating every printed label with no warning.
  Fix (policy A recommended — keep DB nfc in sync + warn to reprint):
  1. `gui_changeUser.apply_changes`: if name or department changed and the admin didn't re-scan, recompute `nfc = f"{fresh_user.id_us}_{new_name}_{department.id_dep}".lower()` (mirror `MatrixCode.py:46` exactly) and pass to `crud.update_user`.
  2. `gui_changeEquip.apply_changes`: if `equipment.nfc` set and name/serialnum changed and no re-scan, and **serialnum is truthy** (mirror the skip at `MatrixCode.py:104`), set `equipment.nfc = f"{equipment_id}_{new_name}_{new_serialnum}".lower()`; keep the uniqueness check block (221-227) around the new value.
  3. In both, when a code-bearing field changed on a row with an nfc, show a persistent `ui.notify(..., color='warning')`: label is now out of date — regenerate and reprint.
  Verify: give a user an nfc, rename, save → DB nfc reflects the new name + reprint warning; download button matches new nfc; old printed label fails to scan, new one resolves.
  Depends on: M3 (recompute could hit an inactive-row collision).

**Commit Step 4** ("Fix wrong-data UI bugs: user selection, rental editor, list refresh, duration sort, report freshness, code resync").

---

## Step 5 — Packaging & repository hygiene

⚠️ **Before any `git rm --cached`, confirm the `rental.db` backup from Step 0 exists and matches the working copy.** The working `rental.db` shows `M` (differs from the committed copy) — the working copy is the real data. Losing it is unrecoverable. Use `git rm --cached` (index only), **never** plain `git rm`, on `rental.db`.

- [ ] **M15 — Web-viewer subprocess broken in frozen builds, double-spawns in native mode, hardcodes the LAN IP**
  Files: `main.py:893,901,905,908,882,881,918,935`.
  Now: (1) the PyInstaller commands never bundle `web_viewer/`; (2) frozen `sys.executable` is the rental exe, so `Popen([sys.executable, viewer_script])` launches a second main app; (3) the `{"__main__","__mp_main__"}` guard makes native mode spawn the viewer twice; (4) hardcoded IP `172.20.124.60`; (5) version skew (title 2.1.5 vs spec 2.1.4).
  Fix:
  1. Wrap only the `subprocess.Popen` section (899-913) in `if __name__ == "__main__":` (keep `main()`/`ui.run` under the existing `{'__main__','__mp_main__'}` guard) — stops the native-mode double spawn.
  2. Frozen: guard the spawn with `if not getattr(sys, "frozen", False):` (Option A, dev-only viewer), OR run the viewer in-process on a background thread (Option B), OR ship a separate viewer exe and Popen it by absolute path (Option C).
  3. Bundle: add `--add-data "<abs>/web_viewer;web_viewer/"` to the 2.1.5 command (935) and the spec; resolve `viewer_script` and the existence check (881, 901) via `APP_DIR` from M2.
  4. Replace the hardcoded IP (882) with a discovered LAN address (UDP socket to `8.8.8.8:80`, read `getsockname()[0]`, fallback `gethostbyname(gethostname())`/`localhost`); only set the label if the viewer actually started.
  5. Reconcile the version string (918) with the build name via a single `VERSION` constant.
  Verify: dev `python main.py` → exactly one PID on `:8585` (`netstat -ano | findstr :8585`). Frozen: build with `web_viewer` bundled, viewer reachable, no second main window. Status label shows the real LAN IP.
  Depends on: M2.

- [ ] **M20 — `web_viewer/` (documented core) and `CLAUDE.md` are untracked**
  Files: `web_viewer/` (0 tracked files); `web_viewer/viewer_app.py`; `CLAUDE.md`.
  Now: a fresh clone lacks the network viewer and the project instructions.
  Fix: `git add web_viewer/` and `git add CLAUDE.md` **by explicit path**. First `git status --porcelain web_viewer/` and reset any `__pycache__`/`.db` inside it. Decide `CODE_REVIEW_REPORT.md` intentionally (commit or gitignore). Commit on `usb_scan` with the trailer. **Never `git add -A`** — the tree has staged doc deletions and untracked venvs that must not be swept in.
  Verify: `git ls-files web_viewer/` returns the viewer source; `git ls-files CLAUDE.md` returns it. Fresh clone + `python main.py` starts the viewer with no FileNotFoundError.
  Depends on: M22.

- [ ] **M21 — Committed spec (2.1) is stale/broken; the working 2.1.4 spec is untracked; both lag 2.1.5**
  Files: `WenglorMEL Rental System 2.1.spec:7,8,25`; untracked `2.1.4.spec:5,7,8,25`; `main.py:918,928-933,935`.
  Now: tracked 2.1 spec has a dead path (missing "My Projects"), `binaries=[]` (no `libdmtx-64.dll` → Data Matrix fails silently), and no `scanner_config.json`. The correct 2.1.4 spec is untracked and one version behind.
  Fix: create `WenglorMEL Rental System 2.1.5.spec` from the untracked 2.1.4 spec's contents, bump `name=` to `...2.1.5`. Make paths portable (SPECPATH/`os.path`-derived) instead of the machine-specific absolute paths. Ensure `binaries` includes `libdmtx-64.dll` and `datas` includes `rental.db`, `scanner_config.json`, `nicegui/`, **and `web_viewer/`** (coordinate with M15). `git rm "WenglorMEL Rental System 2.1.spec"`, `git add` the new spec. Fix the stale build comment in `main.py:928-933` (keep only the correct recipe). Commit with trailer.
  Verify: `pyinstaller "WenglorMEL Rental System 2.1.5.spec"`; the exe title reads 2.1.5, Data Matrix generation succeeds (DLL bundled), `scanner_config.json` present. `git ls-files *.spec` returns exactly one current spec.
  Depends on: M22.

- [ ] **M22 — Runtime artifacts tracked in git; `.gitignore` incomplete**
  Files: `.gitignore:1-41`; tracked `rental.db`, `logs/scanner.log`, `scanner_config.json`, 19 `*.pyc`, `WenglorMEL Rental System 2.1.exe`; partially-tracked `.hypothesis/`.
  Now: `.gitignore` entries are inert because the files are already tracked; git shows perpetual `M rental.db`/`M logs/scanner.log`/`M *.pyc`.
  Fix:
  1. **Back up `rental.db` first** (Step 0). Confirm the working copy is authoritative.
  2. `git rm --cached rental.db logs/scanner.log scanner_config.json "WenglorMEL Rental System 2.1.exe"`.
  3. `git rm --cached -r __pycache__ gui/__pycache__ .hypothesis`.
  4. Append to `.gitignore`: `logs/`, `*.exe`, `.hypothesis/`, `.nicegui/`, `output*/`, `data/`, `bnrs/`, `bnrs_old/`, and (from M5) `rental.db-wal`, `rental.db-shm`. Keep the existing `__pycache__/`, `*.db`, `rental.db` lines (now effective).
  5. `scanner_config.json` is bundled into the exe **and** written at runtime: commit a `scanner_config.default.json` template, gitignore the live `scanner_config.json`, and have the app/build fall back to the template. Do not silently drop it.
  Verify: `git ls-files | grep -E '\.pyc$|\.exe$|^logs/|^rental\.db$|scanner_config\.json$'` returns nothing (or only the template). After running the app + a scan, `git status` is clean. Fresh clone has no bytecode, live DB, logs, or venv dirs.
  Depends on: M20, M21 (same commit workflow — sequence: back up → untrack artifacts + extend .gitignore → add missing source + spec → commit).

- [ ] **M23 — `requirements.txt` incomplete (no pytest/pytest-asyncio/pyinstaller) and unbounded; NiceGUI floor 2.0.0 vs 3.8.0 used**
  Files: `requirements.txt:1,2,6` and missing entries.
  Now: a fresh env from requirements can't run tests or build; all pins are unbounded `>=`; `hypothesis` (test-only) is a runtime dep.
  Fix:
  1. Keep runtime deps in `requirements.txt`: SQLAlchemy, NiceGUI, pylibdmtx, Pillow, hidapi, pyscard, pywebview. Move `hypothesis` out.
  2. Create `requirements-dev.txt`: `pytest>=9,<10`, `pytest-asyncio>=1.3,<2`, `hypothesis>=6.151,<7`, `pyinstaller>=6.19,<7`.
  3. Add ceilings to runtime pins (installed versions): `NiceGUI>=3.8,<4` (highest risk), `SQLAlchemy>=2.0.25,<3`, `Pillow>=12,<13`, `pywebview>=6,<7`, `pyscard>=2.3,<3`, `hidapi>=0.15,<1`, `pylibdmtx>=0.1.10`.
  4. Optionally `pip freeze > requirements.lock` (excluding the unused auto-py-to-exe/Eel/bottle/gevent bloat). Update CLAUDE.md/README: `requirements.txt` for runtime, `requirements-dev.txt` before pytest/build.
  Verify: clean venv → `pip install -r requirements.txt` + `python main.py` imports cleanly; `pip install -r requirements-dev.txt` + `pytest` collects; `pyinstaller` builds; NiceGUI resolves to 3.x (not 4.x).

**Commit Step 5** (split into "Untrack runtime artifacts; extend .gitignore", "Track web_viewer/CLAUDE.md + current spec", "Fix viewer spawn & bundling", "Split runtime/dev requirements" as appropriate).

---

## Step 6 — Scanner support-file fixes

M19 must precede M18 (if `read_scan` truncates, the corrupted-vs-timeout distinction is moot). All line numbers in `usb_hid_scanner.py`/`scanner_config.py`/`scanner_logging.py` as noted.

- [ ] **M16 — `configure_scanner.py` imports six functions (+`update_config`) that no longer exist → ImportError**
  Files: `configure_scanner.py:15-22,101,120,146,48,186`; `scanner_config.py:43-260`.
  Now: import fails at line 15; the whole config schema it references (`legacy_nfc`, `timeouts.*`, `behavior.*`, `performance.*`, `platform.*`) is obsolete. No other module imports it (dead standalone script).
  Fix (recommended): **delete `configure_scanner.py`** — it's unreferenced, fully broken, and the admin scanner-config GUI already provides runtime configuration. (If it must be kept: rewrite against the current API — `load_config`/`set_scanner_mode`/`update_usb_config`/`save_config(copy.deepcopy(DEFAULT_CONFIG))`; change `--mode` choices to `['usb_vendor','keyboard']`; remove the timeout/toggle-focus/optimize/import subcommands that map to absent keys.)
  Verify: `grep -r configure_scanner *.py` returns nothing after delete.

- [ ] **M19 — `read_scan` terminator check breaks on any NUL/CR/LF; hardcodes `read(64)`/utf-8; ignores config**
  Files: `usb_hid_scanner.py:176,183,246,54-69`; `NfcScan.py:300,725`; `scanner_config.py:33-34`.
  Now: `read(64)` and `decode('utf-8')` hardcoded (config `read_size`/`encoding` ignored); the terminator check breaks on the first NUL padding, truncating multi-report scans.
  Fix:
  1. Extend `USBHIDScanner.__init__` to `(self, vid, pid, timeout=30, read_size=64, encoding='utf-8')`; store `self.read_size`, `self.encoding`.
  2. Line 176 → `data = self.device.read(self.read_size)`.
  3. Line 246 → `decoded = cleaned_data.decode(self.encoding)`.
  4. Both instantiation sites: read `read_size`/`encoding` from `usb_config` (get_usb_config already loaded at 262-265 / 716-719) and pass them: `USBHIDScanner(vid, pid, timeout, read_size, encoding)` at `NfcScan.py:300` and `:725`.
  5. Fix the terminator (183): drop the `b'\x00'` clause → `if b'\n' in accumulated_data or b'\r' in accumulated_data:`. Add a quiet-period completion: track `last_data_time`; if `accumulated_data` non-empty and no new data for ~0.15 s, treat the scan as complete. Keep the global NUL/CR/LF strip in `_parse_hid_report` (242) so interior padding is still removed.
  Verify: unit-test `read_scan` with a fake device returning a payload split over two 64-byte NUL-padded reports ending in `\r` — assert the full reassembled string. Set non-default `read_size`/`encoding` in config and assert they're used. A long real Data Matrix scans to "found".
  (Hardware note: exact framing is Wenglor-specific; confirm the quiet-period value against a real device.)

- [ ] **M18 — `except UnicodeDecodeError` in `get_usb_hid_input` is unreachable → corrupted scans reported as "Scan Timeout"**
  Files: `usb_hid_scanner.py:244-250,197-207`; `NfcScan.py:430-445,413-428`; `scanner_error_dialogs.py:245-303`.
  Now: `read_scan` never raises (all exceptions caught internally, returns str/None), so the `except UnicodeDecodeError` handler is dead and corrupted scans fall through to the timeout branch.
  Fix (Option A minimal): define `class CorruptedScanError(Exception): pass` at the top of `usb_hid_scanner.py`; `_parse_hid_report`'s inner `except UnicodeDecodeError` (248-250) raises it; `read_scan` catches it above the generic handler and returns a sentinel `'__CORRUPTED__'`; in `NfcScan.py` handle `if scan_data == '__CORRUPTED__':` (show `ScannerErrorDialogs.show_corrupted_data_error()`) before the truthiness test at 384 — **and guard the background call site at `:742/:744`** so the sentinel isn't treated as a valid payload. Then remove the dead `except UnicodeDecodeError` (430-445), moving its retry logic into the corrupted branch. (Option B cleaner: return a `(data, reason)` tuple and update both call sites.)
  Verify: feed `read_scan` invalid UTF-8 via unit test → corrupted sentinel/reason produced; a scanner emitting non-UTF-8 shows "Invalid Scan Data", not "Scan Timeout".
  Depends on: M19, C1.

- [ ] **connect-leaks-hid-handle — `connect()` leaks the opened HID handle when post-open calls raise**
  Files: `usb_hid_scanner.py:97-99,110,115,120`.
  Now: if `set_nonblocking`/`get_manufacturer_string`/`get_product_string` raise after `open()`, all three except branches set `self.device = None` without `close()`, leaking the handle.
  Fix: add `def _safe_close(self): if self.device is not None: try: self.device.close() except Exception: pass`. Call `self._safe_close()` before each `self.device = None` (110, 115, 120), keeping the subsequent `raise PermissionError`/`return False`.
  Verify: unit-test a fake `hid.device` whose `open()` succeeds but `get_manufacturer_string()` raises IOError → `connect()` returns False (or raises PermissionError) and `close()` was called exactly once.

- [ ] **load-config-nested-merge-noop — nested merge is a self-update; missing nested keys never backfilled**
  Files: `scanner_config.py:143-151`.
  Now: `merged_config.update(config)` replaces nested dicts wholesale, then `merged_config['usb_vendor'].update(config['usb_vendor'])` updates the object with itself — a no-op; missing keys aren't restored (currently masked by `.get(key, default)` downstream).
  Fix: after `merged_config = copy.deepcopy(DEFAULT_CONFIG)` (144), delete 145 and 147-151; insert:
  ```python
  for key, value in config.items():
      if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
          merged_config[key].update(value)
      else:
          merged_config[key] = value
  ```
  Leave the VID/PID validation (153-159) unchanged.
  Verify: write `{"scanner_mode":"keyboard","usb_vendor":{"vid":1234}}`, call `load_config()`, assert `usb_vendor.timeout==30`, `read_size==64`, `encoding=='utf-8'`, `vid==1234`, `scanner_mode=='keyboard'`.

- [ ] **save-config-non-atomic — truncate-in-place write; a crash mid-write leaves corrupt JSON silently replaced by defaults**
  Files: `scanner_config.py:185-196`.
  Now: `open(config_path,'w')` + `json.dump` can leave a truncated file; `load_config` then returns defaults, discarding the user's mode/VID/PID.
  Fix: `import os`; write to `tmp_path = config_path.with_suffix('.json.tmp')`, `json.dump`, `f.flush()`, `os.fsync(f.fileno())`, then `os.replace(tmp_path, config_path)`. Keep the try/except returning False; on failure `try: os.remove(tmp_path) except OSError: pass`. (Combine with `scanner-config-blocking-and-half-save` in Step 7.)
  Verify: patch `json.dump` to raise after the temp file is created → original `scanner_config.json` intact, `save_config` returns False; normal save/load round-trips a custom mode/VID.

- [ ] **check-connection-polling — `_check_connection` (a USB control transfer) runs every loop iteration (~100/s)**
  Files: `usb_hid_scanner.py:168-194,191,209-224`.
  Now: `_check_connection` issues `get_manufacturer_string()` every iteration for the whole read window (~3000 transfers over 30 s).
  Fix: throttle to ~1/s — before the loop add `last_conn_check = 0.0`; wrap 191-194 in `now = time.time(); if now - last_conn_check > 1.0: last_conn_check = now; if not self._check_connection(): …`. (Alternative: remove the periodic check entirely and rely on `read()`'s IOError, already caught at 200 — verify `_check_connection` has no other callers first.)
  Verify: instrument `_check_connection` with a counter; a 5 s no-scan read → ~5 calls, not ~500. Unplug mid-read still returns None and flips `is_connected()` False.

- [ ] **setup-logging-clobber-rotate-payloads — clears ALL root handlers, unbounded FileHandler, PII payloads at INFO**
  Files: `scanner_logging.py:47-51,61-66`; `usb_hid_scanner.py:259`; `NfcScan.py:385,745`.
  Now: `logging.getLogger().handlers.clear()` drops other libraries' handlers; plain `FileHandler` grows unbounded (git-tracked); scan payloads (`{id}_{name}_…`, i.e. PII) logged at INFO.
  Fix:
  1. Use a dedicated `logging.getLogger('scanner')` with `propagate=False` instead of the root logger; or, minimally, track and remove only the handlers this function added (not `.clear()`).
  2. Make `setup_logging` idempotent (don't stack duplicate handlers on repeat calls).
  3. Replace the `FileHandler` with `from logging.handlers import RotatingFileHandler` → `RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding='utf-8')`.
  4. Stop logging raw payloads at INFO: `usb_hid_scanner.py:259` → log length only; `NfcScan.py:385` and `:745` → "scan received" without the value (or DEBUG).
  5. Untrack `logs/` (M22); gitignore `scanner.log.*` backups.
  Verify: call `setup_logging` twice → no duplicated handlers, other loggers' handlers survive; emit >1 MB → rotates to `scanner.log.1`; a successful scan → raw payload absent at INFO.

**Commit Step 6** ("Scanner support: config threading, atomic save, corrupted-scan signal, logging hygiene, handle-leak fix").

---

## Step 7 — Remaining Minor fixes (grouped by file)

### `crud.py` / data-layer
- [ ] **serialnum-default-false** — `models.py:14`. Now: `Column(String, default=False)` stores 0. Fix: change to `Column(String, default=None)` (or just `Column(String)`). Optional one-time cleanup: `UPDATE equipment SET serialnum = NULL WHERE serialnum = '0';`. Verify: insert without serialnum → stored NULL; UI shows empty S/N.
- [ ] **update-cannot-reactivate** — `crud.py:27,69,113,29,30,71,115`. Now: `update_equipment/etype/department` fetch via status-filtered getters (can't reactivate) and truthiness guards block clearing. Fix: add `get_equipment_including_inactive`/`get_etype_including_inactive`; give the three updaters an `including-inactive` fetch (or a `get_*_func` param like `update_user`); change `if name:`/`if serialnum:` to `if name is not None:` (guard NOT-NULL columns against empty). Verify: soft-delete an Etype, `update_etype(id, status=True)` reactivates it. Depends on: M3.
- [ ] **update-user-mutates-before-validate** — `crud.py:159,160,165,168,173`. Now: name/dep/status applied before the nfc dup check that can raise, leaving dirty state in the long-lived session. Fix: reorder so all validation (dept lookup 161-163, nfc dup check 167-171) runs before any mutation; wrap commit in `_commit(db)`. Verify: `update_user` with a valid name + a taken nfc → raises AND name unchanged on a fresh session. Depends on: M4.
- [ ] **stats-outerjoin-negated** — `crud.py:454,455,471,639,641,707,709,723`. Now: `>0` filter/`HAVING` after `outerjoin` (and an inner `.join` in department stats) makes the "never rented" else branches dead. Fix (product decision): to show never-rented rows, relax/remove the `>0` filters (user 455, name HAVING 641) and change department `.join`→`.outerjoin` (707) removing 709; else delete the dead else branches (471-473, 656-658, 723-725) with a comment. Reference the correct pattern in `get_equipment_rental_summary` (334-343). Verify per chosen policy.
- [ ] **notin-null-vuln** — `crud.py:286,287,299,300`. Now: a single NULL `equipment_id` in the open-rental subquery empties the Available list app-wide. Fix: add `Rental.equipment_id != None` to both subqueries (287, 300), or rewrite as NULL-safe `~db.query(Rental).filter(Rental.equipment_id == Equipment.id_eq, Rental.rental_end == None).exists()`. Verify: insert a rental with NULL `equipment_id` → Available list still correct. Depends on: M5.
- [ ] **nfc-payload-ambiguity** — `MatrixCode.py:46,106`; `fill_nfc_fields.py:40,57`. Now: user/equipment codes share the `{id}_{name}_{x}` format → cross-table collision. Fix (breaking): prefix user codes `u_…` and equipment `e_…` in both files; regenerate all nfc columns via "Update codes" and **reprint all labels**. Verify: a would-be colliding user/equipment now differ by prefix and each scan resolves correctly. (Weigh reprint cost — low real-world probability.)
- [ ] **tz-naive-timestamps** — `models.py:55`; `crud.py:214,241,394`; `duration_utils.py:58`. Now: naive local timestamps distort durations across DST; folds silently clamp to 0. Fix (migration-touching — **consider deferring**): store UTC (`datetime.now(datetime.timezone.utc)`, `DateTime(timezone=True)`), convert to local only at display, log rather than silently zero negatives. Requires a one-shot conversion of existing naive rows (no mixing aware/naive). Verify: a DST-straddling rental computes wall-clock-correct duration.

### `main.py` / main-app
- [ ] **return-dialog-always-reports-success** — `main.py:227,228,229`; `crud.py:237`. Now: unconditional "Equipment returned successfully!" even for an already-returned rental. Fix: make `crud.return_equipment` return True only when it actually closed the rental (idempotent), False otherwise; branch the toast on the result. Verify: return once → success; trigger again → "already returned".
- [ ] **session-reused-after-with-closed** — `main.py:707,711,765,788,801,825`. Now: `show_add_nfc_dialog` uses `fresh_db` after its `with` block closed (works only via SQLAlchemy silently reopening). *Currently dead code* (caller commented at 825). Fix: open a short-lived `with SessionLocal() as s:` inside each callback (scan_nfc 765, on_save 788), or keep a session open for the dialog lifetime and close it on dismiss. Decide whether to restore or delete the function. Verify (if restored): uncomment 825, scan + Apply, code persists, no detached-instance errors.
- [ ] **admin-gesture-docstring-and-password** — `main.py:654,665,669,643`. Now: docstring says "5 clicks / 0.4s" but code is 3 clicks / 0.8s; password hardcoded `"supp"`. Fix: correct the docstring; extract `ADMIN_CLICK_COUNT=3`, `ADMIN_CLICK_WINDOW_SEC=0.8`; load the password from env/config (not real auth per CLAUDE.md — don't overclaim). Verify: triple-click within 0.8s opens the dialog; password comes from config.

### `main.py` + `gui/*` (shared)
- [ ] **tkinter-tk-in-worker-threads** — `main.py:443,444,459,484,485,500`; `gui/gui_changeUser.py:111,123`; `gui/gui_changeEquip.py:107,119`. Now: `tk.Tk()` created via `run.io_bound` (worker thread) — unsafe, hangs/crashes on Windows. Fix: replace the tkinter folder picker with pywebview's `app.native.main_window.create_file_dialog(webview.FOLDER_DIALOG)` (correct thread), or run Tk on the main thread (not `run.io_bound`) with a single reused hidden root; in pure-browser mode fall back to a NiceGUI download. Apply to all four sites. Verify: on native Windows, open Generate/Download Codes and pick a folder 5+ times each — never freezes/crashes.

### `gui/*` dialogs
- [ ] **dead-none-validation-add-dialogs** — `gui/gui_adduser.py:94,96,130`; `gui/gui_addequip.py:87,89,126`. Now: validation compares against literal `'None'`/`'Selected: '` that never appear; real placeholder text passes → raw backend error. Fix: track the selection in a nonlocal (`selected_dep`/`selected_etype`) and validate `if not name or not selected_x`; or compare against the actual placeholder string; drop the no-op `.replace('Selected: ', '')`. Verify: Add Device with a name but no type → friendly warning, not a raw "not found".
- [ ] **cancelled-scan-code-lie** — `gui/gui_changeUser.py:92,102`; `gui/gui_changeEquip.py:88,99,221`; `crud.py:166`. Now: a cancelled scan flips the label to "Not set" while the DB keeps the old code (update skips `None`); no way to intentionally clear a code. Fix: on cancel, leave `nfc_value` unchanged and restore the label to the real stored state; add a "Clear code" button that sets a sentinel; make clearing persist as `nfc = None` (not `''` — two empty strings collide on UNIQUE). Verify: scan then cancel on a coded user → indicator stays "Code scanned"; Clear → nfc NULL after save.
- [ ] **stale-dropdown-data-add-dialogs** — `gui/gui_addequip.py:19,123`; `gui/gui_adduser.py:19,22,128`. Now: module-level `data` loaded once at import; renames elsewhere never refresh it; `refresh_departments` is dead code. Fix: add `refresh_etypes()` (with `db.expire_all()`) and call it at the top of `show_add_equipment_dialog`; actually call `refresh_departments()` at the top of `show_add_user_dialog`. Verify: rename a type/department, open the Add dialog without restart → new name shown and add succeeds.
- [ ] **empty-row-leak-cancelled-scan** — `gui/gui_addequip.py:80,81`; `gui/gui_adduser.py:88,89`. Now: cancelled-scan else-branch opens a new `ui.row()` just to set an attribute, leaking an empty row each time. Fix: remove the `with ui.row()...` wrapper — set `nfc_label.content` directly. (Coincides with cancelled-scan-code-lie.) Verify: cancel-scan repeatedly → no empty rows accumulate.
- [ ] **unbounded-dialog-accumulation** — `gui/gui_changeUser.py:222`; `gui/gui_changeEquip.py:240`; `gui/gui_changeDep.py:169`; `gui/gui_changeEtype.py:160`; `gui/gui_changeRental.py:427,494`. Now: a fresh `ui.dialog()` per open, never deleted; auto-reopen timers add more. Fix: register `dialog.on('hide', lambda: dialog.delete())`; add `parent_dialog.delete()` after `close()` in the auto-reopen path, or reuse a single dialog per editor. Verify: open/close Edit Users ~50× → q-dialog node count doesn't grow unbounded.
- [ ] **dead-zero-rental-filter-8x** — `gui/gui_reports.py:152,200,275,319,397,442,702,747`. Now: 8 list-comprehensions filter for `'0'`/`''` that the `'D:HH:MM'` strings never equal (and crud already excludes zero rows) — dead code. Fix: delete all 8 comprehension lines, assign the raw stats directly. Verify: each stats report shows an unchanged row set. Depends on: M12 (if numeric filtering is later desired, use `total_rental_seconds`).
- [ ] **scanner-config-blocking-and-half-save** — `gui/gui_scanner_config.py:73,175,124,259,262,264,273`. Now: `check_connection_status()`/`refresh_devices()` run synchronously during dialog build (UI freezes; spinner never renders); save does two independent writes → half-saved config on partial failure. Fix: make `show_scanner_config_dialog` async, open the dialog first, then `await run.io_bound(...)` for the blocking USB calls (spinner renders); make save atomic (single write of vid+pid+mode, coordinate with `save-config-non-atomic`) and report per-part results if split. Verify: dialog appears immediately with a visible spinner while devices load; a simulated partial-save failure names which half failed.
- [ ] **bulk-status-commit-order — NOT REPRODUCED** — `gui/gui_changeDep.py:151,156,159`; `gui/gui_changeEtype.py:142,147,150`; `crud.py:196,206`. The reported partial-update cannot occur: the rename and the bulk `User.status`/`Equipment.status` UPDATE flush in a **single transaction**, so a UNIQUE-constraint failure rolls both back atomically. Fix: none required for correctness. Optional cleanup: move the "Updated status for N …" `ui.notify` after the final commit; add explicit try/except+rollback (ties into M4). **Do not split into two commits** — that would introduce the bug the report feared. Verify: rename a department to a colliding name with "Apply to All Users" → no user.status changed, name unchanged.

### Web viewer
- [ ] **web-viewer-shared-module-session** — `web_viewer/viewer_app.py:21,45,306,100`. Now: one module-level `db` shared by all clients; up-to-30s staleness and an `ObjectDeletedError` window on hard-deleted rentals. Fix: replace with per-fetch `with SessionLocal() as db:` in each read site (ViewerState 24-37, apply_combined_filters 190, reset_filter 261, full_refresh 299, show_rental_history 108). Since the app is read-only, per-fetch is simplest and removes the staleness. Verify: two LAN clients; rename an item and delete a rental in the main app → both reflect it on next refresh, no `ObjectDeletedError`.
- [ ] **web-viewer-readonly-and-storage-secret** — `web_viewer/viewer_app.py:14,21,376,381`. Now: read-only by convention only; `create_all` runs; hardcoded `storage_secret`; binds `0.0.0.0`. Fix: give the viewer its own **read-only** engine (`sqlite:///file:<abs>/rental.db?mode=ro&uri=true`, absolute path from M2) and a viewer-local sessionmaker (stops `create_all` writing); move `storage_secret` to env/config with a strong random value; reconsider/​document the `0.0.0.0` exposure. Test the WAL+read-only combination together (a pure `?mode=ro` connection may fail to create `-wal`/`-shm`). Verify: any write via the viewer's session raises "attempt to write a readonly database"; normal viewing works; `storage_secret` from config. Depends on: M2.

**Commit Step 7** (group by file/area as convenient).

---

## Step 8 — Info / cleanup (optional, low priority)

- [ ] **echo-true** — `database.py:9`. Change `echo=True` → `echo=False` (optionally `echo=os.environ.get('BNRS_SQL_ECHO','')=='1'`). Batch with the M5 edit (same `create_engine` line). Verify: console no longer prints SQL/params during rent/return.
- [ ] **dead-code-get-card-uid** — `NfcScan.py:192-225,8-11`. Delete unused `get_card_uid()` and the three now-unused `smartcard` imports (verify no other `smartcard`/`readers`/`toHexString`/`CardConnectionException`/`NoCardException` references first). If `pyscard` is unused repo-wide, drop it from `requirements.txt`. Verify: `python -c "import NfcScan"` imports cleanly.
- [ ] **dead-code-scanning-active** — `NfcScan.py:23`. Delete the unused `scanning_active = False` global. Verify: import clean, grep shows no references.
- [ ] **matrixcode-engine-leak** — `MatrixCode.py:33,93`. Now: a new engine per call, never disposed. Fix: `from database import SessionLocal` and use it (best — shares the WAL engine), or add `engine.dispose()` in the finally (74, 134). Verify: loop `update_user_codes()` many times → no growth in open connections.
- [ ] **duration-utils-docstring-overflow** — `duration_utils.py:24,115,119,51`. Now: docstring example inconsistent; `format_duration_from_seconds(float('inf'))` raises OverflowError. *Module currently unused.* Fix: correct the docstring to a self-consistent `{'duration':'1:02:35','duration_seconds':95730.0}`; add `import math`; after the `<=0` check, `if math.isinf(total_seconds) or math.isnan(total_seconds): return 'Active rental'`. Coordinate with M12's owner before adopting vs. deleting the module. Verify: `format_duration_from_seconds(float('inf'))` returns a string; `(95730)` returns `'1:02:35'`.
- [ ] **Env/venv drift note (informational).** The tracked `*.pyc` are cpython-313 while the active venv is Python 3.11.9 — stale build noise (removed in M22). The venv also carries unused bloat (auto-py-to-exe/Eel/bottle/gevent) that must **not** be added to `requirements.txt` (M23).

**Commit Step 8** ("Cleanup: dead code, docstrings, echo=False, engine disposal").

---

## Regression checklist (manually drive after all steps)

Use the `run` skill to launch the native app (port 15716) and the `verify` skill where noted.

1. **Scan-to-rent (usb_vendor):** valid code → workflow proceeds once, no `InvalidStateError`. Cancel mid-scan → nothing fires; dialog reopens immediately.
2. **Scan-to-rent error paths:** wrong VID/PID → connection dialog *before* any toast; Retry 3× → three real attempts then max-retries notice; "Use Keyboard Mode" → one coherent outcome, config flips to `keyboard`.
3. **Scan-to-return:** returns exactly once; double-click Confirm → one toast; already-returned → "already returned".
4. **Keyboard mode:** ESC the scan dialog → app keeps keyboard focus.
5. **Manual rent:** rent to a user; try to rent the same item again (stale card) → warning, no second open rental. Select Alice, close via X, open another item, Confirm without selecting → "Please select a user!".
6. **Manual return:** returns; report freshness — reopen Rental History without restart → returned row shows real timestamp + duration.
7. **Add/edit equipment & users:** add with no filter → card appears immediately. Edit a name → reprint warning + DB nfc resynced. Re-add a soft-deleted name/code → friendly warning, not IntegrityError. Try to deactivate a rented item → blocked.
8. **Rental editor:** two same-named units — editing the second doesn't reassign to the first. Edit a rental whose user was soft-deleted (comment-only) → saves.
9. **Reports & durations:** 9-day vs 85-day users → descending lists 85 first; toggle ascending correct; "Active rental" rows group at one end.
10. **Code regeneration:** run "Update codes", download a label, scan the new one → resolves; old label fails (expected).
11. **Tests:** `pytest` runs clean; `git status` shows no `M rental.db` / `M scanner_config.json`.
12. **Build:** `pyinstaller "WenglorMEL Rental System 2.1.5.spec"` → exe title 2.1.5, Data Matrix generation works (DLL bundled), `scanner_config.json` + `web_viewer/` present.
13. **Different CWD / frozen:** run `python <abs>/main.py` from another directory and the moved exe → same `rental.db`, no empty DB created.
14. **LAN viewer:** exactly one process on `:8585`; status label shows the real LAN IP; two clients reflect a rename/delete with no `ObjectDeletedError`; a write attempt raises read-only.
15. **Config robustness:** simulate a crash mid-`save_config` → `scanner_config.json` intact. Set non-default `read_size`/`encoding` → honored. Corrupted scan → "Invalid Scan Data", not "Scan Timeout".

---

## Coverage table

79 finding entries across 7 areas → **74 unique IDs** (the 5 IDs marked *(2 areas)* were reported from two review areas each and are handled once).

| ID | Title (short) | Step |
|----|----------------|------|
| C3 | Tests mutate live rental.db | 1 |
| C4 | Tests rewrite live scanner_config.json | 1 |
| test-defeated-pytest-guard | `pytest=None` fallback dies at decorator | 1 |
| test-background-scanner-zero-coverage | Skipped/no-assert test | 1 |
| test-integration-main-always-passes | main() always "passed" | 1 |
| test-silent-pass-on-importerror | ImportError swallowed → green | 1 |
| test-wrong-shape-mocks | USB mock returns bare string | 1 |
| test-tautology-status-values | Self-referential assertion | 1 |
| test-interface-shape-only | Introspection-only, duplicated | 1 |
| test-device-enumeration-flakiness | Hardware-dependent/unused param | 1 |
| test-heavy-duplication | Mode/signature tests duplicated 6×+ | 1 |
| C1 | USB retry resolves `closed` too early / double-resolve | 2 |
| C2 | Dialogs not persistent → orphaned futures/loops | 2 |
| M17 | Cancel race in get_usb_hid_input | 2 |
| missing-done-guards-nfcscan | Unguarded `set_result` | 2 |
| disconnect-during-executor-read | close() races read() | 2 |
| retry-counter-double-increment | Retry counter +2 per click | 2 |
| contradictory-keyboard-fallback-ux | Two toasts, no restart | 2 |
| error-dialogs-retry-double-increment-and-done-guards | Dialog guards + increment | 2 |
| M2 *(2 areas: data-layer, main-app)* | Relative DB path / frozen `__file__` | 3 |
| M4 | Bare commits poison sessions (rollback helper) | 3 |
| M3 *(2 areas: data-layer, gui-dialogs)* | Dup checks blind to soft-deleted | 3 |
| M5 | No WAL/busy_timeout/FK | 3 |
| M6 | Soft-deleting rented equipment | 3 |
| M7 *(2 areas: data-layer, main-app)* | No double-rental protection | 3 |
| M8 | Stale `state.selected_user` | 4 |
| M9 | Rental editor resolves by name | 4 |
| M10 | Editor can't save inactive-entity rentals | 4 |
| M11 | New equipment invisible without filter | 4 |
| M12 | Duration sorts lexicographically | 4 |
| M13 *(2 areas: main-app, gui-dialogs)* | Reports show stale rentals | 4 |
| M14 | Edits don't resync nfc payload | 4 |
| M15 | Viewer subprocess broken/double-spawn/IP | 5 |
| M20 | web_viewer/ & CLAUDE.md untracked | 5 |
| M21 | Stale/untracked PyInstaller specs | 5 |
| M22 | Runtime artifacts tracked in git | 5 |
| M23 | requirements.txt incomplete/unbounded | 5 |
| M16 | configure_scanner.py ImportError | 6 |
| M19 | read_scan terminator/read_size/encoding | 6 |
| M18 | Unreachable UnicodeDecodeError handler | 6 |
| connect-leaks-hid-handle | connect() leaks HID handle | 6 |
| load-config-nested-merge-noop | Nested merge no-op | 6 |
| save-config-non-atomic | Non-atomic config write | 6 |
| check-connection-polling | ~100 control transfers/s | 6 |
| setup-logging-clobber-rotate-payloads | Root-handler clobber/PII/unbounded | 6 |
| serialnum-default-false | String column `default=False` | 7 |
| update-cannot-reactivate | update_* can't reactivate | 7 |
| update-user-mutates-before-validate | Mutate before validate | 7 |
| stats-outerjoin-negated | Dead never-rented branches | 7 |
| notin-null-vuln | NOT IN emptied by NULL | 7 |
| nfc-payload-ambiguity | Cross-table code collision | 7 |
| tz-naive-timestamps | Naive local timestamps (defer) | 7 |
| return-dialog-always-reports-success | Always "returned successfully" | 7 |
| session-reused-after-with-closed | fresh_db used after close (dead code) | 7 |
| admin-gesture-docstring-and-password | Docstring/password | 7 |
| tkinter-tk-in-worker-threads *(2 areas: main-app, gui-dialogs)* | Tk on worker thread | 7 |
| dead-none-validation-add-dialogs | Dead 'None' validation | 7 |
| cancelled-scan-code-lie | Cancel lies about code | 7 |
| stale-dropdown-data-add-dialogs | Stale add-dialog dropdowns | 7 |
| empty-row-leak-cancelled-scan | Leaked empty ui.row | 7 |
| unbounded-dialog-accumulation | Dialog DOM growth | 7 |
| dead-zero-rental-filter-8x | Dead zero-rental filter ×8 | 7 |
| scanner-config-blocking-and-half-save | Blocking dialog / half-save | 7 |
| bulk-status-commit-order | **NOT REPRODUCED** (optional cleanup) | 7 |
| web-viewer-shared-module-session | Shared viewer session | 7 |
| web-viewer-readonly-and-storage-secret | Read-only/secret/bind | 7 |
| echo-true | engine echo=True | 8 |
| dead-code-get-card-uid | Dead pyscard path | 8 |
| dead-code-scanning-active | Unused global | 8 |
| matrixcode-engine-leak | Engine per call, not disposed | 8 |
| duration-utils-docstring-overflow | Docstring/inf (unused module) | 8 |

**Count check:** 74 unique IDs listed = 79 finding entries − 5 cross-area duplicates. Every JSON finding is accounted for.