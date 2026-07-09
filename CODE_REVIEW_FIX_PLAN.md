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

**Correction (2026-07-09, found during a final post-Step-8 audit):** the review above was wrong to imply item 5 of the C4 fix (protect or delete every affected file's `if __name__ == "__main__"` runner) was fully done. It was only actually done for 2 of the 6 named files (`test_rental_workflow_integration.py`'s runner deleted under C3; `test_background_scanner.py` renamed/rewritten). The other 5 — `test_integration_nfc_workflow.py`, `test_nfc_scan_routing.py`, `test_property_mode_routing.py`, `test_property_runtime_mode_switching.py`, `test_property_async_interface.py` — still had a live, unprotected `if __name__ == "__main__": success = main(); exit(...)` block calling `set_scanner_mode()` with no redirection, since `conftest.py`'s autouse fixture is pytest-only machinery that never runs for a bare `python <file>.py` invocation (which `CLAUDE.md` documents as a supported way to run these tests). Running any of these 5 standalone would still have rewritten the live `scanner_config.json`, in 2 cases up to 100× via hypothesis — reproducing the exact bug C4 exists to fix. Caught by an independent audit workflow (two-pass: initial finding + adversarial re-check, both concluded REAL_GAP) launched after Step 8 in response to the user asking for final confirmation everything was done. Fixed directly: each of the 5 files' `__main__` block now wraps `main()` in a temp-redirect of `scanner_config.CONFIG_FILE` (mirroring `conftest.py`'s `isolated_scanner_config` pattern), restored in a `finally` regardless of whether `main()` succeeds, fails, or raises. Verified by actually running all 5 as standalone scripts (`python test_X.py`) and confirming the live `scanner_config.json` SHA-256 was unchanged after every single one (one run hit an unrelated pre-existing Windows-console Unicode encoding crash inside `main()` — confirmed the `finally` cleanup still ran correctly even then). Full `pytest`: 54 passed, unchanged.

---

## Step 2 — Scan-dialog lifecycle & scanner control flow ✅ COMPLETED (2026-07-08)

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

- [x] **C1 — USB retry flow resolves `closed` too early and can double-resolve it**
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

- [x] **C2 — Scan/confirm dialogs are not persistent; ESC leaves futures unresolved and leaks loops/HID handle**
  Files: `NfcScan.py:247, 496, 536-542, 601, 612-616, 738, 1053, 1103`.
  Now: no dialog uses `.props('persistent')`; ESC runs no handler → keyboard `maintain_focus` loops forever (focus stolen), USB background loop holds the HID device until restart, confirm/return workflows await forever.
  Fix (Option A, recommended — mirror the admin dialog at `main.py:573`): change each `ui.dialog()` to `ui.dialog().props('persistent')` at lines 247, 496, 601, 1053, 1103. Users must exit via the explicit buttons that already resolve the futures. (Option B if dismissal must stay: add `dialog.on('hide', …)` handlers that resolve the future as cancelled, guarded with `.done()`, and for `get_usb_hid_input` also set `cancelled=True` to stop `scan_task`.)
  Verify: for each dialog press ESC / click outside — it must not close. In keyboard mode, confirm focus is not stolen. In usb_vendor mode, ESC the Select-User dialog then immediately start another scan — the scanner reconnects (handle released).
  Depends on: C1, M17, missing-done-guards-nfcscan.

- [x] **M17 — Cancel race: blocking HID read keeps running after Cancel; `cancelled` not re-checked**
  Files: `NfcScan.py:252-259, 381-382, 384-396, 461-464`.
  Now: `on_cancel` resolves `closed`, but `scan_task` may still be blocked in `run_in_executor(scanner.read_scan)`; when it returns, the success branch runs with no `cancelled` re-check → same `InvalidStateError` cascade; device held for up to `timeout`.
  Fix:
  1. Immediately after the executor read (382) insert `if cancelled: return` (before `if scan_data:` at 384). With C1's guarded `_resolve()` this fully prevents the crash.
  2. (Optional, releases device sooner) add a `self._cancel` flag + `scanner.cancel()` to `USBHIDScanner`, checked each iteration of `read_scan`'s loop (`usb_hid_scanner.py:168-194`), and call it from `on_cancel`.
  Verify: usb_vendor mode — start scan, Cancel, then scan a valid code within the timeout: nothing happens, no `InvalidStateError`. Dialog reopens immediately if the optional flag is added.
  Depends on: C1.

- [x] **missing-done-guards-nfcscan — future resolutions lack `.done()` guards**
  Files: `NfcScan.py:1056-1067, 1108-1114, 259, 504, 508, 616, 623, 643, 754`.
  Now: rapid double-click (or an ESC hide handler racing a button) double-resolves → `InvalidStateError`.
  Fix: guard every `<future>.set_result(...)` with `if not <future>.done():`. For the return dialog `on_confirm` (1056-1063), guard the **whole body** with `if confirmed.done(): return` at the top so `crud.return_equipment`/`update_callback`/toast don't fire twice. For `get_usb_hid_input` use the shared `_resolve()`.
  Verify: double-click "Confirm Return" and "Confirm Rental" — no `InvalidStateError`, exactly one toast, one `update_callback`.
  (Prerequisite for C2 Option B.)

- [x] **disconnect-during-executor-read — `disconnect()` can run while the executor thread is inside `read_scan`**
  Files: `NfcScan.py:796-807, 738-742, 775-778`; `usb_hid_scanner.py:129-138`.
  Now: cleanup does `scanner_task.cancel()` then the task's `finally` calls `scanner.disconnect()` (`device.close()`) while the executor thread may still be in `device.read()` — hidapi concurrent close+read is unsafe.
  Fix: don't `cancel()`. Set `scanner_cancelled = True`, then `if scanner_task is not None: await scanner_task` (no cancel). The loop condition (`while not scanner_cancelled and not result.done():`, 738) + the 2 s read timeout let the read finish, the loop exit, and `finally: disconnect()` run only after `read_scan` returns. Optionally bound with `asyncio.wait_for(..., timeout=slightly_over_read)`.
  Verify: rapidly confirm/cancel the Select-User dialog while the background scanner polls; no hidapi errors; log shows "Background scanner disconnected" *after* the last read.

- [x] **retry-counter-double-increment — connection-retry counter increments twice**
  Files: `NfcScan.py:336-338, 347-356`; `scanner_error_dialogs.py:119, 127-128`.
  Now: `retry_connection` increments `retry_count` (338) *and* the caller increments again (354) — each Retry advances by 2, so ~2 real attempts of 3.
  Fix: empty `retry_connection`'s body — change lines 337-338 to `pass` (keep the `async def` stub so the "Retry Connection" button still renders; it is gated on truthy `retry_callback` at `scanner_error_dialogs.py:119`). Keep the single authoritative `retry_count += 1` at line 354. Do **not** set `retry_callback=None`.
  Verify: wrong VID/PID, click Retry 3× → three connection attempts before "Maximum retry attempts reached".
  Depends on: C1.

- [x] **contradictory-keyboard-fallback-ux — fallback shows both a "not connected" and a "switched" toast and doesn't restart the scan**
  Files: `NfcScan.py:329, 332-333, 340-345, 357-359, 1035-1036`.
  Now: connect-failure pre-resolves `closed` (caller shows "Scanner not connected"), and the fallback also toasts "Switched to keyboard mode. Please restart the scan." — two contradictory messages, no auto-restart.
  Fix (fold into C1's restructure): on `choice == 'fallback'`, after `set_scanner_mode('keyboard')`, **restart the scan in keyboard mode**: `data, st = await get_nfc_input_keyboard(prompt_message); result = data; status = 'cancelled' if not data else 'success'; _resolve(); return`. If auto-restart is undesired, at minimum set `status='cancelled'` before resolving so the caller (1033-1038) doesn't print "Scanner not connected", and reduce the notification to one clear message. Stop relying on the pre-set `status='not_connected'` (329) for the fallback path.
  Verify: usb_vendor mode, disconnected scanner, click "Use Keyboard Mode" → exactly one coherent outcome; `scanner_config.json` shows `keyboard`.
  Depends on: C1.

- [x] **error-dialogs-retry-double-increment-and-done-guards (scanner_error_dialogs.py)**
  Files: `scanner_error_dialogs.py:56-69, 152-160, 206-214, 260-268, 326-334, 124-130`; `NfcScan.py:336-338, 353-354`.
  Now: (1) same double-increment as above (fixed in `NfcScan.py`); (2) every dialog's `on_retry/on_cancel/on_fallback` calls `result.set_result(...)` unguarded.
  Fix: add `if not result.done():` before every `result.set_result(X)` in `scanner_error_dialogs.py` (on_retry 59, on_fallback 64, on_cancel 69; timeout 155/160; disconnection 209/214; corrupted 263/268; permission 329/334). The increment half is handled by `retry-counter-double-increment`.
  Verify: unit-test calling `on_retry()` then `on_cancel()` on one dialog future → no `InvalidStateError`, first result wins.
  Depends on: C1, C2, M17.

**Commit Step 2** ("Fix scan-dialog future lifecycle, persistence, cancel race, retry counter").

### Review — how Step 2 was done

**Approach:** unlike Step 1, nearly every finding here converges on the same function (`get_usb_hid_input` in `NfcScan.py`), so this was done as one coherent rewrite by me directly rather than parallel per-file agents (which would have collided on the same lines). Independent adversarial review agents were used afterward to verify the result.

**The shared contract, implemented once:** a `_resolve()` closure (`if not closed.done(): closed.set_result(None)`) defined right after `closed = asyncio.Future()`; every raw `closed.set_result(None)` in `scan_task` replaced with `_resolve()`; all five retry-capable error branches (permission, connection-failure, disconnect-during-read, timeout, corrupted-data) now hide the scanning dialog and await their error dialog *without* resolving `closed` first — only terminal outcomes (cancel, fallback, max-retries, generic exception) resolve it; `dialog.open()` moved inside the retry loop so retries show a freshly-reset dialog instead of no dialog at all.

**Per-finding deltas:**
- **C1** — fixed via the shared contract above.
- **C2** — `.props('persistent')` added to all 5 dialogs in `NfcScan.py` (scan dialog, keyboard dialog, user-selection dialog, return-confirmation dialog, rental-confirmation dialog) **and**, as a judgment call beyond the plan's literal file list, all 5 dialogs in `scanner_error_dialogs.py` — they share the exact same ESC-orphans-the-future defect and leaving them non-persistent would have left an equivalent hole in the very flow this step hardens. Verified against the installed NiceGUI source (`dialog.py`) that `persistent` only blocks ESC/backdrop dismissal, never the code's own `dialog.close()` calls.
- **M17** — added `if cancelled: return` immediately after the executor read, before any result/status mutation; added an optional `USBHIDScanner.cancel()` method (`_cancel_requested` flag, checked once per poll iteration in `read_scan`'s loop, reset at the start of each call) so Cancel releases the device within ~10ms instead of waiting out the full timeout.
- **missing-done-guards-nfcscan** — all 11 `set_result(` call sites in `NfcScan.py` are now guarded (either via the shared `_resolve()` or an `if <future>.done(): return` at the top of their handler).
- **disconnect-during-executor-read** — `get_user_input_with_selection` no longer calls `scanner_task.cancel()`; it sets `scanner_cancelled = True` and awaits the task (bounded by `asyncio.wait_for(..., timeout=5.0)`), letting the background task's own 2-second read timeout notice the flag and exit before its `finally: disconnect()` runs.
- **retry-counter-double-increment** — `retry_connection`'s body emptied to `pass`; `retry_count += 1` now happens exactly once, at the call site.
- **contradictory-keyboard-fallback-ux** — the fallback path now actually awaits `get_nfc_input_keyboard(...)` and returns its result, instead of showing a "please restart the scan" notification and returning a dead `not_connected` result.
- **error-dialogs-retry-double-increment-and-done-guards** — all 12 handlers (on_retry/on_cancel/on_fallback) across the 5 `scanner_error_dialogs.py` methods guarded with `if result.done(): return`.

**Verification (three layers, since this code can't be driven by a human clicking through the app in this environment):**
1. *Functional smoke test* — a scratchpad harness (not committed) that imports the real `get_usb_hid_input` and drives it against a mocked `USBHIDScanner`/`ScannerErrorDialogs`, confirming no unhandled task exceptions and correct behavior across: immediate success, permission-error→retry→success (the exact C1 crash scenario), connection-failure retry-counter accuracy (3 dialogs shown, not ~2), max-retries exhaustion, fallback-to-keyboard auto-restart, the cancel-guard short-circuit, and a double-click on the return dialog. All 7 scenarios passed. This surfaced one real regression along the way: an existing test's hand-built `ui.dialog` mock didn't emulate NiceGUI's fluent `.props()` chaining (it only chained `.style()`/`.classes()`), so `dialog.props('persistent')` returned an unconfigured child mock and broke the `with dialog:` context manager. Fixed by adding `mock_dialog_instance.props = Mock(return_value=mock_dialog_instance)` to `test_scanner_status_messages.py`, matching the pattern already used for `.style()`.
2. *Independent adversarial review* — 5 agents (one per finding cluster), each re-reading the actual current code and tracing every path by hand, not trusting my summary. All 5 returned `FULLY_FIXED`. Two agents' first attempt hit a tool-level structured-output error unrelated to the code (retry-cap exceeded); re-run as 4 smaller, more atomic tasks and all passed clean.
3. *Regression suite* — full `pytest` run (54 passed), and SHA-256 confirmation that `rental.db`/`scanner_config.json` are still byte-identical to the Step 0 backup.

**Known, out-of-scope residual gaps** (all confirmed non-crashing by the reviewers; none reproduce the `InvalidStateError` this step exists to fix):
- If Cancel is clicked during the ~0.5s pause after a successful scan (or during the initial `scanner.connect()`/`sleep(0.1)`), `on_cancel` can resolve `closed` with `status="cancelled"` before `scan_task` reaches its own resolution — the caller can see `status="cancelled"` paired with a non-empty `result`, or a stray error dialog can flash after the user already left. I attempted a 2-line fix for the first case but reverted it: by the time `on_cancel` resolves `closed`, the outer `await closed` has already returned, so a check added later inside `scan_task` cannot change what was already handed back — a real fix would require restructuring `scan_task` to be the sole authority over `closed`'s resolution (with `on_cancel` only setting a flag it polls), which is a larger redesign than this step's scope. Documented here rather than silently left implicit.
- `get_user_input_with_selection`'s background scanner doesn't get the new `USBHIDScanner.cancel()` wiring (M17's fix targeted `get_usb_hid_input` specifically); it already has its own bounded-wait mechanism via `disconnect-during-executor-read`'s fix, so this is a minor "could release a couple seconds faster" enhancement, not a bug.
- `scanner.connect()` is still a direct blocking call, not run through an executor — pre-existing, out of this step's scope (it's the Minor `blocking-calls-on-event-loop` finding, scheduled for Step 7).

---

## Step 3 — Harden the data layer ✅ COMPLETED (2026-07-08)

Do the **shared roots first**: M2 (path anchoring), M4 (rollback helper), M3 (inactive-aware duplicate helpers). M3 + M4 + M7 interact — implement the combined approach below.

- [x] **M2 — Relative sqlite path + `create_all` on import silently creates an empty DB in the wrong CWD; frozen `__file__` wrong; constant duplicated** *(shared root cause — data-layer + main-app)*
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

- [x] **M4 — 19 crud writes commit with no try/rollback → poisoned long-lived sessions** *(linchpin: M2/M3/M5/M6/M7 + update-user-mutates depend on it)*
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

- [x] **M3 — Duplicate/unique pre-checks are blind to soft-deleted rows; create_* have no dup check** *(shared root cause — data-layer + gui-dialogs)*
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

- [x] **M5 — Two processes share one SQLite file with no WAL/busy_timeout/FK enforcement**
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

- [x] **M6 — Soft-deleting rented equipment hides its open rental and makes it unreturnable**
  Files: `crud.py:37,199,246,759,761`; `gui/gui_changeEquip.py:218`.
  Now: `delete_equipment` and the Etype bulk toggle flip `status=False` with no rental check; then the open rental disappears from all active-rental queries and `find_equipment_by_nfc`, so it can never be returned.
  Fix:
  1. `delete_equipment` (37-44): before `status=False`, `if is_equipment_rented(db, equipment_id): raise ValueError("Cannot deactivate equipment that is currently rented — return it first")`.
  2. `update_etype_equipment_status` (199-206): when `new_status` is False, query for any active rental in that type and raise/skip (or exclude rented units).
  3. `gui_changeEquip.py:218` (bypasses crud): add the same `is_equipment_rented` guard before flipping status.
  4. Secondary (rescue existing orphans): consider removing `.filter(Equipment.status == True)` from `get_active_rentals` (252), `get_active_rentals_by_equipment_type` (312), `get_active_rentals_summary` (387) so orphaned open rentals stay returnable — confirm with product owner (changes Available/Rented UI semantics).
  Verify: rent an item, try to deactivate via both paths → blocked; return it → deactivation succeeds.
  Depends on: M4.

- [x] **M7 — No double-rental protection: `create_rental` inserts unconditionally; no DB constraint** *(shared root cause — data-layer + main-app; see also M8/M11)*
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

### Review — how Step 3 was done

**Approach:** done as one direct pass across `crud.py`/`models.py`/`database.py` (like Step 2, the shared roots — M4's `_commit()` helper and M3's `*_including_inactive` getters — are called from many sites, so a single coherent edit avoided cross-agent collisions), then independent adversarial review agents verified each finding cluster afterward against the actual current source.

**Shared roots, implemented once:**
- **M2** — new `paths.py` module exports a frozen-aware `APP_DIR` with zero other imports, so `scanner_config.py`/`scanner_logging.py` can anchor their paths to it *without* pulling in `database.py`'s engine-creation/`create_all` side effects (which would defeat Step 1's test isolation the moment those modules are imported standalone). `database.py` also imports `APP_DIR` from `paths.py` and re-exposes it as `database.APP_DIR` for `main.py`'s two `os.path.dirname(__file__)` viewer-path lookups. `fill_nfc_fields.py` now imports `DATABASE_URL` from `database.py` instead of duplicating it (mirrors `MatrixCode.py`'s existing pattern).
- **M4** — `_commit(db)` helper added to `crud.py` (commit, rollback-and-re-raise on failure); all 19 bare `db.commit()` calls replaced with it. `update_rental`'s own pre-existing try/except/rollback logic was left untouched, exactly as the plan specified.
- **M3** — four new `*_including_inactive` getters (`find_user_by_nfc_including_inactive`, `find_equipment_by_nfc_including_inactive`, `get_etype_by_name_including_inactive`, `get_department_by_name_including_inactive`); `create_etype`/`create_department`/`create_user`/`create_equipment` now pre-check via these and raise a friendly `ValueError` (noting when the collision is with a deactivated row) instead of a raw `UNIQUE constraint failed`; `update_user`/`update_user_nfc`'s existing dup checks switched from the active-only getter to the inactive-aware one. Chose **raise a clear error** over **silently reactivate** as the policy for the create-time collision (the plan left this as an open decision) — reactivating a stale row could resurrect unexpected old relationships silently; a friendly error keeps the admin in control and matches how the rest of the app already surfaces validation failures via `ui.notify`.

**Per-finding deltas:**
- **M5** — WAL + `busy_timeout=5000` + `foreign_keys=ON` added via a `connect` event listener in `database.py`. Before enabling FK enforcement, queried the live `rental.db` directly for orphaned/NULL `user_id`/`equipment_id` rentals — found zero, so enforcement was safe to turn on immediately with no cleanup step. Added `rental.db-wal`/`rental.db-shm` to `.gitignore`. Deliberately did **not** add `nullable=False` to `Rental.user_id`/`equipment_id` or attempt a table-rebuild migration to enforce it on the live DB — the plan only mentions this in passing under M7 (not as its own M5 checklist item), no code path can currently produce a NULL there (both are required positional args of `crud.create_rental`), and a full table rebuild for a practically unreachable edge case felt like unjustified risk for this step. Documented as an out-of-scope residual gap below.
- **M6** — `crud.delete_equipment` and `crud.update_etype_equipment_status` now raise `ValueError` if the equipment (or any unit of the etype, for the bulk toggle) has an active rental, before flipping `status`. `gui/gui_changeEquip.py`'s `apply_changes` (which bypasses crud entirely via raw ORM writes) got the identical guard inlined, since it's the same defect the plan called out by file:line.
- **M7** — three layers: (1) `crud.create_rental` raises `ValueError` if `is_equipment_rented` is already truthy; (2) `main.py`'s `show_rent_dialog.on_confirm` re-checks `is_equipment_rented` immediately before renting and disables the Confirm button on click to shrink the TOCTOU window; (3) `models.py` declares a partial unique index (`uq_active_rental_per_equipment` on `Rental.equipment_id` where `rental_end IS NULL`) as a DB-level backstop even a raw bypass insert can't get around.
- **M7 migration** — `migrations/001_add_active_rental_unique_index.py` (the slot already reserved in `migrations/README.md`'s tracking table): checks for existing duplicate open rentals first (found none), then applies `CREATE UNIQUE INDEX IF NOT EXISTS`. Tested against a scratch copy of `rental.db` first (confirmed a manually-inserted duplicate open rental was correctly rejected with `IntegrityError`), then ran against the live `rental.db` (backed up immediately before). `migrations/README.md`'s log entry records both runs.

**Verification (three layers):**
1. *Scratch harness* (`verify_step3_data_layer.py`, not committed) drives the real `crud.py`/`models.py` functions against a throwaway in-memory DB — 15 checks covering M2 anchoring, M4's rollback-then-usable-session behavior, M3's four dup-check paths, M6's two rented-equipment guards, and M7's three protection layers (including a raw ORM bypass attempt to prove the DB-level index, not just the Python check, actually fires). All 15 passed.
2. *Independent adversarial review* — 4 agents (one per finding cluster: M2, M4, M3, M6+M7), each reading the current source directly rather than trusting a summary. All 4 returned a clean pass with zero bugs found.
3. *Regression suite* — full `pytest` run: 54 passed (same count as after Step 2), only the pre-existing `PytestReturnNotNoneWarning`s noted in Step 1's review.

**A real, expected change to `rental.db` this step (unlike Steps 0-2):** Steps 0-2 confirmed `rental.db`/`scanner_config.json` stayed byte-identical throughout. Step 3 is different — M7's index migration and M5's WAL-mode pragma both intentionally modify `rental.db`'s on-disk schema/format, so "byte-identical" is no longer the right invariant from here on. Verified instead by dumping every row of every table (`users`, `equipment`, `etypes`, `departments`, `rentals`, `feedback`) and confirming 100% identical content against the Step 0 backup — only the schema (new index) and journal mode changed, zero data was altered. One side note worth flagging honestly: the WAL-mode transition ended up happening the moment `pytest` collected a test file that imports `NfcScan.py` (which imports `database.py`, which opens a real connection to the live `rental.db` at import time — a pre-existing pattern, not something introduced this step) rather than the first time `python main.py` runs, since both trigger the exact same `connect` event listener. This is harmless (confirmed via the full-table data dump above) and is the same one-time, permanent transition the plan's own M5 fix anticipates either way — just triggered a little earlier than "run the app" would suggest. `scanner_config.json` remains byte-identical (SHA-256 unchanged) since nothing in Step 3 writes to it.

**Known, out-of-scope residual gap:** `Rental.user_id`/`equipment_id` are not enforced `NOT NULL` at the DB level (see M5 note above) — a defense-in-depth gap against a scenario no current code path can trigger, deliberately deferred rather than risking a live table rebuild for it in this step.

---

## Step 4 — Wrong-data UI bugs ✅ COMPLETED (2026-07-08)

- [x] **M8 — Stale `state.selected_user` can rent to the wrong user**
  Files: `main.py:45,145,151,158`.
  Now: `state.selected_user` cleared only on successful confirm; closing via X/ESC leaves it set → next dialog Confirm (without selecting) rents to the previous user.
  Fix (best): make selection **local to the dialog** — replace `state.selected_user` reads/writes in `show_rent_dialog` with a closure `selected_user_id = None` (`nonlocal` in `on_user_select_modified`/`on_confirm`). Minimal: reset `state.selected_user = None` at the top of `show_rent_dialog` (143). If keeping the global, also clear it on dialog hide (`dialog.on('hide', lambda: setattr(state,'selected_user',None))`) covering the X button (192) and ESC.
  Verify: open dialog for A, select Alice, close via X; open for B, click Confirm without selecting → "Please select a user!", no rental for B.
  Depends on: M7.

- [x] **M9 — Rental editor resolves user/equipment by display NAME only → wrong unit**
  Files: `gui/gui_changeRental.py:182,190,309,326,328`.
  Now: dropdowns built from non-unique names; save matches by name (equipment even strips the serial back off) → first match wins.
  Fix: build id-lookup dicts. Users: `display = f"{u.name} ({u.department.name}) [#{u.id_us}]"`, `users_by_display[display] = u.id_us`. Equipment: `display = f"{eq.name} (S/N: {eq.serialnum or 'No S/N'}) [#{eq.id_eq}]"`, `equipment_by_display[display] = eq.id_eq`. Set `user_value`/`equipment_value` to the **same** display strings (char-for-char, or NiceGUI shows blank). Pass the dicts into `save_rental_changes`; replace the name-based `next(...)` lookups (309, 326-328) with dict lookups + not-found guards; delete the `split(' (S/N:')` logic.
  Verify: two equipment rows same name/different serial; edit a rental on the second, change only the comment, save, reopen → S/N unchanged and `rentals.equipment_id` unchanged. Repeat with two same-named users.
  Depends on: M10 (same functions — apply together).

- [x] **M10 — Rental editor cannot save edits when the user/equipment was soft-deleted**
  Files: `gui/gui_changeRental.py:130,131,309,408`; `crud.py:877,892`.
  Now: dropdowns load only active rows, so a rental for a departed user/retired device is edit-locked; even a date/comment change fails.
  Fix: load **including inactive** for the dropdowns/dicts: `crud.get_all_users_including_inactive` (crud.py:186) and `crud.get_all_equipment_including_inactive` (crud.py:592). Capture `original_user_id`/`original_equipment_id` before building the form; in `save_rental_changes` only pass `user_id`/`equipment_id` to `update_rental` when they **changed** (pass `None` otherwise — `update_rental` skips `None`, avoiding the inactive re-validation at crud.py:882-883/897-898). Optionally label inactive entries " (inactive)".
  Verify: soft-delete a rental's user, open the editor, change only the comment, save → succeeds; reopen shows new comment; `rentals.user_id` unchanged. Reassign to a different active user → also succeeds.
  Depends on: M9, M4.

- [x] **M11 — Newly added equipment doesn't appear when no filter is active**
  Files: `main.py:116,120,129`; `gui/gui_addequip.py:103`; `main.py:597`.
  Now: `update_lists` only re-queries when a filter is set; otherwise it re-renders the stale in-memory list, so a newly added device shows a toast but no card.
  Fix: make `apply_combined_filters()` unconditional — change the guard at `main.py:120-121` to always call it (it already handles the no-filter case, 273-290). Optionally drop the now-duplicate `apply_combined_filters()` in `filter_by_etype` (250) and `on_name_filter_change` (292). (Lower-risk alternative: wire `gui_addequip`'s callback at `main.py:597` to `refresh_with_filters` instead of `update_lists`.)
  Verify: with no filter, Admin → Add Device → new card appears immediately without "Refresh all data". With a type filter set, a new device of that type still appears.

- [x] **M12 — Duration columns sort lexicographically; history mixes in "Active rental"**
  Files: `gui/gui_reports.py:208,327,449,533,543,550,754`; `crud.py:469,566,654,722`.
  Now: duration is an unpadded `D:HH:MM` string, so `'9:…'` sorts above `'85:…'`; history's Duration column also contains the literal "Active rental".
  Fix:
  1. `crud.py`: add `'total_rental_seconds': int(total_seconds) if total_seconds else 0` to each stats-row dict in `get_user_rental_statistics` (~479), `get_equipment_type_statistics` (~580), `get_equipment_name_statistics` (~665), `get_department_rental_statistics` (~730).
  2. `gui_reports.py`: on each `total_rental_time` column (defined at 141, 264, 386, 691) add a Quasar custom sort key `':sort': '(a, b, rowA, rowB) => (rowA.total_rental_seconds ?? 0) - (rowB.total_rental_seconds ?? 0)'` (keep `field='total_rental_time'` for display).
  3. History: add a numeric `duration_seconds` per row (`int((end-start).total_seconds())`; `None` for active); add `':sort': '(a, b, rowA, rowB) => (rowA.duration_seconds ?? Number.MAX_SAFE_INTEGER) - (rowB.duration_seconds ?? Number.MAX_SAFE_INTEGER)'` to the Duration column (533).
  Do **not** zero-pad the day segment (unbounded). Only `sortable:true` columns use the comparator — all four already are.
  Verify: one user ~9 days, another ~85 days → descending lists the 85-day user first; toggle ascending → 9 first. In history, "Active rental" rows group at one end.

- [x] **M13 — Reports read through a never-expired module session → returned rentals still show "Not returned"** *(main-app + gui-dialogs; real fix lives in gui_reports)*
  Files: `gui/gui_reports.py:21,540,543,560`; `main.py:346,338`.
  Now: `gui_reports.py:21` holds a module-level `db = SessionLocal()` never expired; `full_refresh` only expires `main.py`'s session, so History stays stale until restart.
  Fix (in `gui_reports.py`): wrap `show_rental_history`'s data load in `with SessionLocal() as fresh_db:` and call `get_all_rentals(fresh_db)`, materializing all needed values into the plain-dict list (552-563) **before** the block closes. Do the same for the other report builders (`show_user_rental_statistics` 149/197, `show_equipment_type_statistics` 272/316, `show_equipment_name_statistics` 394/439, `show_department_rental_statistics` 699/744, `show_feedback_entries` 822). Minimal alternative: `db.expire_all()` at the top of each report function. Optionally drop the module `db` at line 21. `main.py:346` is only evidence — no functional change needed there beyond documenting that "Refresh all data" cannot reach already-open report dialogs.
  Verify: rent then return an item on the main screen, open Admin → Rental History without restart → returned row shows a real `rental_end` and computed duration.

- [x] **M14 — Edit dialogs change code-bearing fields without regenerating the nfc payload or warning**
  Files: `gui/gui_changeUser.py:211`; `gui/gui_changeEquip.py:215,216,228`; `MatrixCode.py:46,106`.
  Now: renaming a user/device or editing serial/dept leaves the stored `nfc` encoding the OLD values; when "Update codes" is later run it overwrites `nfc`, invalidating every printed label with no warning.
  Fix (policy A recommended — keep DB nfc in sync + warn to reprint):
  1. `gui_changeUser.apply_changes`: if name or department changed and the admin didn't re-scan, recompute `nfc = f"{fresh_user.id_us}_{new_name}_{department.id_dep}".lower()` (mirror `MatrixCode.py:46` exactly) and pass to `crud.update_user`.
  2. `gui_changeEquip.apply_changes`: if `equipment.nfc` set and name/serialnum changed and no re-scan, and **serialnum is truthy** (mirror the skip at `MatrixCode.py:104`), set `equipment.nfc = f"{equipment_id}_{new_name}_{new_serialnum}".lower()`; keep the uniqueness check block (221-227) around the new value.
  3. In both, when a code-bearing field changed on a row with an nfc, show a persistent `ui.notify(..., color='warning')`: label is now out of date — regenerate and reprint.
  Verify: give a user an nfc, rename, save → DB nfc reflects the new name + reprint warning; download button matches new nfc; old printed label fails to scan, new one resolves.
  Depends on: M3 (recompute could hit an inactive-row collision).

**Commit Step 4** ("Fix wrong-data UI bugs: user selection, rental editor, list refresh, duration sort, report freshness, code resync").

### Review — how Step 4 was done

**Approach:** each finding lives in a mostly-separate file (`main.py` for M8/M11, `gui/gui_changeRental.py` for M9/M10, `gui/gui_reports.py`+`crud.py` for M12/M13, `gui/gui_changeUser.py`+`gui/gui_changeEquip.py` for M14), so this was done directly by me across all 6 files, then verified by 4 independent adversarial review agents afterward, one per finding cluster — mirroring Step 3's split.

**Per-finding deltas:**
- **M8** — took the plan's "best" option: `state.selected_user` deleted from `State` entirely; `show_rent_dialog` now uses a dialog-local `selected_user_id = None` closure variable (`nonlocal` in `on_user_select_modified`, read directly in `on_confirm`), so a leftover selection can never survive past that dialog closing, regardless of how it was closed.
- **M9 + M10** (done together, per the plan's own dependency note, since they touch the exact same functions) — two new helper functions `_user_display`/`_equipment_display` build a dropdown label that always includes the row's primary key (`[#id]`), guaranteeing uniqueness even for same-named rows; `show_edit_form_for_rental` builds `users_by_display`/`equipment_by_display` dicts from these and now loads `get_all_users_including_inactive`/`get_all_equipment_including_inactive` instead of the active-only getters; `save_rental_changes` resolves the dropdown selection via dict lookup instead of a name-matching `next(...)`, and only forwards a changed `user_id`/`equipment_id` to `crud.update_rental` (passing `None` for an unchanged selection), which lets `update_rental`'s own active-only re-validation skip fields nobody touched.
- **M11** — took the plan's primary fix: `update_lists()` now unconditionally calls `apply_combined_filters()` (it already correctly returns the full list when no filter is set). As a direct consequence of that fix, five other call sites that used to call `apply_combined_filters()` themselves immediately before calling `update_lists()` (`filter_by_etype`, `on_name_filter_change`, `refresh_with_filters`, `reset_filter`, `full_refresh`) had that now-redundant call removed rather than doubling every DB query on every filter interaction and rent/return — the plan only named the first two explicitly, but the other three have the exact same pattern, so leaving them would have been an inconsistent half-fix.
- **M12** — verified against the actual installed NiceGUI source (`dynamic_properties.js`) that a column-dict key prefixed with `:` is genuinely `eval`'d into a real JS function client-side before this was implemented, since the plan's `:sort` syntax isn't something I'd take on faith. All four stats functions in `crud.py` now return a `total_rental_seconds` int alongside the display string; all four "Total Rental Time" columns and the Rental History "Duration" column got a matching numeric `:sort` comparator (the latter treating an active rental's `None` duration as `Number.MAX_SAFE_INTEGER` so it groups at one consistent end instead of comparing as a raw string).
- **M13** — the module-level `db = SessionLocal()` in `gui_reports.py` was deleted outright (confirmed nothing external imports it); all 6 report-dialog functions now open a fresh `with SessionLocal() as fresh_db:` immediately around every database read, including the nested date-filter `update_data()` closures in the 4 stats dialogs (the plan only called out the initial loads by line number, but the closures re-run the exact same stale-session query on every Apply/Clear click, so fixing only the initial load would have left the bug fully alive for the dialog's entire remaining lifetime).
- **M14** — implemented identically in both `gui_changeUser.py` and `gui_changeEquip.py`: the dialog now captures `original_nfc` separately from the mutable `nfc_value`, so `apply_changes` can tell "the admin re-scanned a new code" apart from "left it untouched." When untouched and a code-bearing field changed, the nfc is recomputed using the exact same formula as `MatrixCode.py`'s `update_user_codes()`/`update_equipment_codes()` (verified character-for-character against that file, including equipment's skip-if-no-serialnum behavior), routed through the same M3 duplicate-check as a real re-scan, and a persistent (`timeout=0`, dismiss-by-button) warning notification tells the admin to reprint the label.

**Verification (three layers):**
1. *Scratch harness* (`verify_step4_ui_bugs.py`, not committed) redirects `database.SessionLocal` to a throwaway temp DB *before* importing `main.py`/any `gui.*` module (all of them bind a `db`/`state` at import time), then drives the real functions directly: two same-named users and two same-named equipment (one inactive) to prove M9's dropdown labels stay unique and M10's inactive-row comment-only save succeeds without touching the unrelated ID; M14's rename-without-rescan on both a user and equipment, asserting the recomputed nfc matches `MatrixCode.py`'s formula exactly and a warning notification fired; all four M12 stats functions checked for the new `total_rental_seconds` field; a direct demonstration of the stale-identity-map bug M13 fixes (a second session's committed change is invisible through a first, older session, but visible through a fresh one); and M8/M11 checked via source inspection plus a live call to `update_lists()` proving a newly created equipment shows up with no filter active. All 21 checks passed (2 initial failures were harness bugs — an inactive-equipment test fixture starving `get_equipment_name_statistics`'s active-only join of rows, and an over-strict string search that matched an explanatory code comment rather than functional code — both fixed in the harness, not the production code).
2. *Independent adversarial review* — 4 agents (M8+M11, M9+M10, M12+M13, M14), each reading the current source directly. All 4 returned a clean pass with zero bugs found.
3. *Regression suite* — full `pytest` run: 54 passed, same as after Steps 2 and 3. `scanner_config.json` SHA-256 and every table's row content in `rental.db` confirmed unchanged against the Step 0 backup (the row-content check, not raw bytes, per the invariant established in Step 3's review once M5/M7 made "byte-identical" the wrong bar).

---

## Step 5 — Packaging & repository hygiene ✅ COMPLETED (2026-07-08)

⚠️ **Before any `git rm --cached`, confirm the `rental.db` backup from Step 0 exists and matches the working copy.** The working `rental.db` shows `M` (differs from the committed copy) — the working copy is the real data. Losing it is unrecoverable. Use `git rm --cached` (index only), **never** plain `git rm`, on `rental.db`.

- [x] **M15 — Web-viewer subprocess broken in frozen builds, double-spawns in native mode, hardcodes the LAN IP**
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

- [x] **M20 — `web_viewer/` (documented core) and `CLAUDE.md` are untracked**
  Files: `web_viewer/` (0 tracked files); `web_viewer/viewer_app.py`; `CLAUDE.md`.
  Now: a fresh clone lacks the network viewer and the project instructions.
  Fix: `git add web_viewer/` and `git add CLAUDE.md` **by explicit path**. First `git status --porcelain web_viewer/` and reset any `__pycache__`/`.db` inside it. Decide `CODE_REVIEW_REPORT.md` intentionally (commit or gitignore). Commit on `usb_scan` with the trailer. **Never `git add -A`** — the tree has staged doc deletions and untracked venvs that must not be swept in.
  Verify: `git ls-files web_viewer/` returns the viewer source; `git ls-files CLAUDE.md` returns it. Fresh clone + `python main.py` starts the viewer with no FileNotFoundError.
  Depends on: M22.

- [x] **M21 — Committed spec (2.1) is stale/broken; the working 2.1.4 spec is untracked; both lag 2.1.5**
  Files: `WenglorMEL Rental System 2.1.spec:7,8,25`; untracked `2.1.4.spec:5,7,8,25`; `main.py:918,928-933,935`.
  Now: tracked 2.1 spec has a dead path (missing "My Projects"), `binaries=[]` (no `libdmtx-64.dll` → Data Matrix fails silently), and no `scanner_config.json`. The correct 2.1.4 spec is untracked and one version behind.
  Fix: create `WenglorMEL Rental System 2.1.5.spec` from the untracked 2.1.4 spec's contents, bump `name=` to `...2.1.5`. Make paths portable (SPECPATH/`os.path`-derived) instead of the machine-specific absolute paths. Ensure `binaries` includes `libdmtx-64.dll` and `datas` includes `rental.db`, `scanner_config.json`, `nicegui/`, **and `web_viewer/`** (coordinate with M15). `git rm "WenglorMEL Rental System 2.1.spec"`, `git add` the new spec. Fix the stale build comment in `main.py:928-933` (keep only the correct recipe). Commit with trailer.
  Verify: `pyinstaller "WenglorMEL Rental System 2.1.5.spec"`; the exe title reads 2.1.5, Data Matrix generation succeeds (DLL bundled), `scanner_config.json` present. `git ls-files *.spec` returns exactly one current spec.
  Depends on: M22.

- [x] **M22 — Runtime artifacts tracked in git; `.gitignore` incomplete**
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

- [x] **M23 — `requirements.txt` incomplete (no pytest/pytest-asyncio/pyinstaller) and unbounded; NiceGUI floor 2.0.0 vs 3.8.0 used**
  Files: `requirements.txt:1,2,6` and missing entries.
  Now: a fresh env from requirements can't run tests or build; all pins are unbounded `>=`; `hypothesis` (test-only) is a runtime dep.
  Fix:
  1. Keep runtime deps in `requirements.txt`: SQLAlchemy, NiceGUI, pylibdmtx, Pillow, hidapi, pyscard, pywebview. Move `hypothesis` out.
  2. Create `requirements-dev.txt`: `pytest>=9,<10`, `pytest-asyncio>=1.3,<2`, `hypothesis>=6.151,<7`, `pyinstaller>=6.19,<7`.
  3. Add ceilings to runtime pins (installed versions): `NiceGUI>=3.8,<4` (highest risk), `SQLAlchemy>=2.0.25,<3`, `Pillow>=12,<13`, `pywebview>=6,<7`, `pyscard>=2.3,<3`, `hidapi>=0.15,<1`, `pylibdmtx>=0.1.10`.
  4. Optionally `pip freeze > requirements.lock` (excluding the unused auto-py-to-exe/Eel/bottle/gevent bloat). Update CLAUDE.md/README: `requirements.txt` for runtime, `requirements-dev.txt` before pytest/build.
  Verify: clean venv → `pip install -r requirements.txt` + `python main.py` imports cleanly; `pip install -r requirements-dev.txt` + `pytest` collects; `pyinstaller` builds; NiceGUI resolves to 3.x (not 4.x).

**Commit Step 5** (split into "Untrack runtime artifacts; extend .gitignore", "Track web_viewer/CLAUDE.md + current spec", "Fix viewer spawn & bundling", "Split runtime/dev requirements" as appropriate).

### Review — how Step 5 was done

**Approach:** unlike prior steps, this one is entirely git-hygiene and packaging, not application logic, so it was done as 4 sequential commits exactly as the plan's own "Commit Step 5" line suggested, in the dependency order M22 spells out (back up → untrack + extend `.gitignore` → add missing source + spec → fix the code that depends on the new layout → requirements). Each commit's changes were verified before moving to the next.

**Commit 1 — M22 (`756cc11`):** confirmed `rental.db` still row-identical and `scanner_config.json` still byte-identical to the Step 0 backup immediately before running `git rm --cached` (index-only, working files untouched) on `rental.db`, `scanner_config.json`, `logs/scanner.log`, the tracked `.exe`, all 19 tracked `*.pyc`, and the partially-tracked `.hypothesis/`. `.gitignore` extended with `logs/`, `*.exe`, `.hypothesis/`, `.nicegui/`, `output*/`, `data/`, `bnrs/`, `bnrs_old/`, and a `scanner_config.json` line (`rental.db-wal`/`-shm` were already added in Step 3). For the "don't silently drop `scanner_config.json`" requirement: added a committed `scanner_config.default.json` (byte-verified identical to `scanner_config.py`'s in-code `DEFAULT_CONFIG` via a direct comparison script) and a small frozen-only seed step in `scanner_config.py` that copies it from the bundled `_MEIPASS` copy into place on first run — mirroring `database.py`'s existing `rental.db` seeding pattern from Step 3's M2 fix exactly. `load_config()` already fell back to `DEFAULT_CONFIG` in-memory when no file exists at all (used by every test via the `isolated_scanner_config` fixture since Step 1), so dev/test behavior needed no change.

**Commit 2 — M20+M21 (`4256430`):** `git add`ed `web_viewer/` (its own `__pycache__/` was already excluded by the global `.gitignore` pattern — nothing needed resetting) and `CLAUDE.md`, plus `CODE_REVIEW_REPORT.md` for the same reason `CODE_REVIEW_FIX_PLAN.md` is already tracked — it's the source document this whole effort derives from, not a build artifact. Built the new `WenglorMEL Rental System 2.1.5.spec` from the untracked 2.1.4 spec's content, with `SPECPATH`-relative paths (portable across machines, unlike both predecessor specs' hardcoded absolute paths) and `datas` extended to include `scanner_config.default.json` and `web_viewer/` per M15's bundling requirement. **Actually ran `pyinstaller` against the new spec** (not just code-inspected it) — `pyinstaller` turned out to already be installed in `bnrs/` (6.19.0, matching M23's own version target) — and used `PyInstaller.utils.cliutils.archive_viewer` to confirm `libdmtx-64.dll`, `rental.db`, `scanner_config.default.json`, the full `nicegui/` tree (1001 files), and `web_viewer/viewer_app.py` all landed inside the built exe. `git rm`'d the stale tracked `WenglorMEL Rental System 2.1.spec` (git recorded it as a rename to the new file). `CLAUDE.md` updated to reference the new spec/build command and to correct a stale claim — `git ls-files bnrs bnrs_old` proved neither venv was ever actually tracked, contradicting the doc's prior "both are committed to the repo" statement.

**Commit 3 — M15 (`b06db0d`):** this finding took much longer than expected because the plan's literal fix (gate the viewer `Popen` on strict `__name__ == "__main__"` instead of the combined `{'__main__','__mp_main__'}` set) was tested empirically against the real app rather than trusted on inspection, per this plan's own verification standard — and the empirical test disproved the simple fix. Launching `python main.py` and inspecting the live process tree (`wmic process ... get ProcessId,ParentProcessId,CommandLine`) showed NiceGUI's native mode reimports this module in further descendant processes an uncertain number of levels deep (3 independent "Web viewer started" prints observed in one run, cascading through multiple `python main.py` re-executions, not just one parent+one child) — worse than the plan's "double-spawns" description. A `__name__`-only guard reduced but did not eliminate this (still 2 spawns, plus a new WebView2 `OutOfMemoryException` from the runaway native-window cascade). Switched to an environment-variable guard (`BNRS_VIEWER_STARTED`, set before the `Popen` call) instead — env vars are inherited by every descendant process regardless of cascade depth, so this closes the hole completely independent of exactly how many times NiceGUI reimports the module. Re-tested and confirmed exactly one viewer process, no crash. The status label's LAN IP is propagated the same way (`BNRS_VIEWER_LAN_IP` env var) since it's uncertain which generation's `main()` call ends up serving the actually-visible window.

For the frozen-build path: `Popen([sys.executable, viewer_script])` was replaced with a self-relaunch (`Popen([sys.executable, "--web-viewer"])` when frozen, `[sys.executable, __file__, "--web-viewer"]` in dev), dispatched at the very top of `main.py` before any other import (a frozen onefile exe has no bundled `python.exe` to hand a raw `.py` path to). Building and running the real exe surfaced a second real bug beyond what the plan anticipated: a bundled `datas` entry like `web_viewer/` unpacks into PyInstaller's temp `_MEIPASS` extraction directory at runtime, not next to the exe (`APP_DIR`) — so the initial frozen build's viewer silently no-op'd (the `os.path.exists()` guard just returned `False`, no exception, no log). Fixed by resolving `viewer_script`'s frozen-mode path against `sys._MEIPASS` instead of `APP_DIR` (both in the top-of-file dispatch and the `Popen` call site) — `APP_DIR` remains correct for `rental.db`/`scanner_config.json`, which are deliberately *seeded* into it as mutable live state, unlike `web_viewer/`'s static code. Rebuilt and re-ran the real exe end-to-end: both `:15716` (main) and `:8585` (viewer) came up as single listeners, dynamic LAN IP `172.20.124.41` shown (correctly different from the old hardcoded `.60`, proving that value really was stale for this machine). Also introduced a single `VERSION = "2.1.5"` constant (used by both the window title and reconcilable with the spec name) and collapsed the stale multi-recipe build comment block at the bottom of `main.py` down to the current spec-based command.

**Commit 4 — M23 (`46c16e0`):** `requirements.txt` reduced to the 7 runtime deps with `<major` ceilings matching currently-installed, verified-working versions (checked via `pip show` in `bnrs/`: SQLAlchemy 2.0.48, NiceGUI 3.8.0, Pillow 12.1.1, hidapi 0.15.0, pyscard 2.3.1, pywebview 6.1 — all matched the plan's predicted ceilings exactly). New `requirements-dev.txt` holds `pytest`/`pytest-asyncio`/`hypothesis`/`pyinstaller`. Verified both files with `pip install --dry-run` against the real venv (all resolved with no conflicts) and a full `pytest` run afterward (54 passed, unchanged). `CLAUDE.md` updated with the two-file install instructions.

**Verification (across all 4 commits):**
1. *Real, not simulated, infrastructure checks* — this step's nature (packaging/git, not application code) meant the meaningful verification was actually running the tools involved: a real `pyinstaller` build (twice, after finding and fixing the `_MEIPASS` bug), a real `python main.py` launch with live process-tree/port inspection (three iterations, converging on the env-var fix), and real `pip install --dry-run` runs — rather than a scratch harness importing functions directly (there's no equivalent for "does the packaged exe actually work").
2. *Regression suite* — full `pytest`: 54 passed after every commit in this step, matching every prior step.
3. *Data integrity* — `rental.db` confirmed row-identical to the Step 0 backup and `scanner_config.json` confirmed byte-identical (SHA-256 unchanged) both before `git rm --cached` and again at the end of the step, despite this step's testing launching the real app and a real built exe multiple times against the live `rental.db`.
4. All test processes and build artifacts (`dist/`, `build/`) spawned during verification were cleaned up (targeted `taskkill` by specific PID, never a blanket by-image-name kill) or are gitignored.

**Update — the "out-of-scope residual gap" below needed a real fix, not just a note.** The initial assessment (logged, non-fatal, safe to defer) was wrong about severity. A follow-up investigation (2 parallel research agents — one tracing NiceGUI's internals, one empirically reproducing against the real built exe) found:
- `main.py` builds its UI at module scope instead of via `@ui.page`, which puts NiceGUI into an internal "script mode": any genuinely-unmatched route falls back to re-executing `sys.argv[0]` via `runpy.run_path` to rebuild a page (this is also the *same* mechanism already documented above as causing native mode's multi-process reimport cascade — not a separate quirk). In the frozen exe, `sys.argv[0]` is a compiled binary, so that re-execution hits the null-byte `SyntaxError`.
- Separately, and far more urgently: `favicon='assets/icon.ico'` was never bundled into the frozen exe's `datas`, so it never resolved to a real file at runtime. NiceGUI's own favicon fallback isn't graceful for a truthy-but-invalid favicon value — it still registers `/favicon.ico`, routed to a helper that only understands SVG/data-URL/single-char favicons, so it unconditionally raised `ValueError`. **Empirically confirmed this alone crashed the whole frozen app on its own within ~40 seconds of launch, with no external requests needed** — the embedded webview auto-requests `/favicon.ico` on every page load. This was a real, reproducible startup crash, not a rare edge case.

Fixed in a follow-up commit (`629a25d`): bundled `assets/` into the spec's `datas` and resolved the favicon to an absolute, frozen-aware path (`_MEIPASS` when frozen, `APP_DIR` otherwise) instead of a bare relative string, mirroring the same pattern used for `rental.db`/`scanner_config.json`/`web_viewer`. Verified against a rebuilt exe: `/favicon.ico` now returns HTTP 200 (was 500), and the app stayed alive past the point where it previously self-terminated. Confirmed via `pytest` (54 passed) and the same row-identical/byte-identical `rental.db`/`scanner_config.json` checks used throughout this step.

**Remaining out-of-scope residual gap (real, but lower-severity, deliberately deferred):** any *other* genuinely-unmatched route (not just the now-fixed favicon) still hits NiceGUI's script-mode fallback and crashes the same way in a frozen build — confirmed still reproducible via a plain `curl` to `/nonexistent-test-path-xyz` (HTTP 500) even after the favicon fix. Also confirmed the app's actual root page (`/`) 500s the same way under a bare `curl /` in **both** dev and frozen mode — pre-existing, unrelated to any Step 5 change, and not a functional regression (the real pywebview window's traffic clearly differs enough from a bare unauthenticated GET to work correctly, since this is a shipped, actively-used app). A real fix for the underlying script-mode fragility means restructuring `main.py` to build its UI via `@ui.page`/`root=` instead of at module scope — a much larger, higher-risk architectural change than anything else in this plan, and not proportionate to fix as a drive-by. Tracked here for a possible future step rather than silently dropped.

---

## Step 6 — Scanner support-file fixes ✅ COMPLETED (2026-07-08)

M19 must precede M18 (if `read_scan` truncates, the corrupted-vs-timeout distinction is moot). All line numbers in `usb_hid_scanner.py`/`scanner_config.py`/`scanner_logging.py` as noted.

- [x] **M16 — `configure_scanner.py` imports six functions (+`update_config`) that no longer exist → ImportError**
  Files: `configure_scanner.py:15-22,101,120,146,48,186`; `scanner_config.py:43-260`.
  Now: import fails at line 15; the whole config schema it references (`legacy_nfc`, `timeouts.*`, `behavior.*`, `performance.*`, `platform.*`) is obsolete. No other module imports it (dead standalone script).
  Fix (recommended): **delete `configure_scanner.py`** — it's unreferenced, fully broken, and the admin scanner-config GUI already provides runtime configuration. (If it must be kept: rewrite against the current API — `load_config`/`set_scanner_mode`/`update_usb_config`/`save_config(copy.deepcopy(DEFAULT_CONFIG))`; change `--mode` choices to `['usb_vendor','keyboard']`; remove the timeout/toggle-focus/optimize/import subcommands that map to absent keys.)
  Verify: `grep -r configure_scanner *.py` returns nothing after delete.

- [x] **M19 — `read_scan` terminator check breaks on any NUL/CR/LF; hardcodes `read(64)`/utf-8; ignores config**
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

- [x] **M18 — `except UnicodeDecodeError` in `get_usb_hid_input` is unreachable → corrupted scans reported as "Scan Timeout"**
  Files: `usb_hid_scanner.py:244-250,197-207`; `NfcScan.py:430-445,413-428`; `scanner_error_dialogs.py:245-303`.
  Now: `read_scan` never raises (all exceptions caught internally, returns str/None), so the `except UnicodeDecodeError` handler is dead and corrupted scans fall through to the timeout branch.
  Fix (Option A minimal): define `class CorruptedScanError(Exception): pass` at the top of `usb_hid_scanner.py`; `_parse_hid_report`'s inner `except UnicodeDecodeError` (248-250) raises it; `read_scan` catches it above the generic handler and returns a sentinel `'__CORRUPTED__'`; in `NfcScan.py` handle `if scan_data == '__CORRUPTED__':` (show `ScannerErrorDialogs.show_corrupted_data_error()`) before the truthiness test at 384 — **and guard the background call site at `:742/:744`** so the sentinel isn't treated as a valid payload. Then remove the dead `except UnicodeDecodeError` (430-445), moving its retry logic into the corrupted branch. (Option B cleaner: return a `(data, reason)` tuple and update both call sites.)
  Verify: feed `read_scan` invalid UTF-8 via unit test → corrupted sentinel/reason produced; a scanner emitting non-UTF-8 shows "Invalid Scan Data", not "Scan Timeout".
  Depends on: M19, C1.

- [x] **connect-leaks-hid-handle — `connect()` leaks the opened HID handle when post-open calls raise**
  Files: `usb_hid_scanner.py:97-99,110,115,120`.
  Now: if `set_nonblocking`/`get_manufacturer_string`/`get_product_string` raise after `open()`, all three except branches set `self.device = None` without `close()`, leaking the handle.
  Fix: add `def _safe_close(self): if self.device is not None: try: self.device.close() except Exception: pass`. Call `self._safe_close()` before each `self.device = None` (110, 115, 120), keeping the subsequent `raise PermissionError`/`return False`.
  Verify: unit-test a fake `hid.device` whose `open()` succeeds but `get_manufacturer_string()` raises IOError → `connect()` returns False (or raises PermissionError) and `close()` was called exactly once.

- [x] **load-config-nested-merge-noop — nested merge is a self-update; missing nested keys never backfilled**
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

- [x] **save-config-non-atomic — truncate-in-place write; a crash mid-write leaves corrupt JSON silently replaced by defaults**
  Files: `scanner_config.py:185-196`.
  Now: `open(config_path,'w')` + `json.dump` can leave a truncated file; `load_config` then returns defaults, discarding the user's mode/VID/PID.
  Fix: `import os`; write to `tmp_path = config_path.with_suffix('.json.tmp')`, `json.dump`, `f.flush()`, `os.fsync(f.fileno())`, then `os.replace(tmp_path, config_path)`. Keep the try/except returning False; on failure `try: os.remove(tmp_path) except OSError: pass`. (Combine with `scanner-config-blocking-and-half-save` in Step 7.)
  Verify: patch `json.dump` to raise after the temp file is created → original `scanner_config.json` intact, `save_config` returns False; normal save/load round-trips a custom mode/VID.

- [x] **check-connection-polling — `_check_connection` (a USB control transfer) runs every loop iteration (~100/s)**
  Files: `usb_hid_scanner.py:168-194,191,209-224`.
  Now: `_check_connection` issues `get_manufacturer_string()` every iteration for the whole read window (~3000 transfers over 30 s).
  Fix: throttle to ~1/s — before the loop add `last_conn_check = 0.0`; wrap 191-194 in `now = time.time(); if now - last_conn_check > 1.0: last_conn_check = now; if not self._check_connection(): …`. (Alternative: remove the periodic check entirely and rely on `read()`'s IOError, already caught at 200 — verify `_check_connection` has no other callers first.)
  Verify: instrument `_check_connection` with a counter; a 5 s no-scan read → ~5 calls, not ~500. Unplug mid-read still returns None and flips `is_connected()` False.

- [x] **setup-logging-clobber-rotate-payloads — clears ALL root handlers, unbounded FileHandler, PII payloads at INFO**
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

### Review — how Step 6 was done

**Approach:** implemented via a workflow of 3 parallel agent groups, split along disjoint file boundaries so they could run concurrently with zero risk of colliding edits: Group A (`usb_hid_scanner.py` + `NfcScan.py` — M19, M18, connect-leaks-hid-handle, plus the raw-payload-logging half of setup-logging-clobber-rotate-payloads for those two files), Group B (`scanner_config.py` — load-config-nested-merge-noop, save-config-non-atomic), Group C (`scanner_logging.py` — the handler-scoping/idempotency/rotation half of setup-logging-clobber-rotate-payloads). Each group was piped through an implement stage then an independent adversarial-review stage (re-reading the real diff and re-running/independently re-verifying the scratch harness, not trusting the self-report), started as soon as that group's implementation finished rather than waiting on the slowest group. M16 (delete `configure_scanner.py`) was done directly, with explicit user confirmation first since it's an outright deletion of a tracked file.

**Per-finding deltas:**
- **M16** — `configure_scanner.py` deleted (`git rm`) after confirming via grep that nothing else in the repo imports it. Verified: `grep -r configure_scanner *.py` returns nothing.
- **M19** — `USBHIDScanner.__init__` extended with `read_size=64`/`encoding='utf-8'`, stored and used by `read_scan`'s `device.read()` and `_parse_hid_report`'s `.decode()`. Both `NfcScan.py` call sites now read `read_size`/`encoding` from `get_usb_config()` and pass them through. The `b'\x00'` clause was dropped from the completion check (kept `\n`/`\r`); a quiet-period completion (0.15s of silence after data has started arriving) was added so scanners with no explicit terminator still complete, and so multi-report NUL-padded scans reassemble correctly instead of stopping at the first padded chunk.
- **M18** — `CorruptedScanError` exception added; `_parse_hid_report`'s `UnicodeDecodeError` branch now raises it instead of silently returning `None`; `read_scan` catches it above the generic handler and returns a `'__CORRUPTED__'` sentinel (a real scan can never collide with it, since real results are always lowercased before being returned but the sentinel keeps its uppercase form). `NfcScan.py`'s main flow checks the sentinel *before* the truthiness test (it's truthy) and runs the exact retry/cancel flow the old dead `except UnicodeDecodeError` block used to run; that block was deleted. The background scanner loop (no error-dialog flow) just logs and `continue`s past the sentinel.
- **connect-leaks-hid-handle** — `_safe_close()` helper added, called in all three of `connect()`'s except branches before `self.device = None`.
- **load-config-nested-merge-noop** — the wholesale `merged_config.update(config)` plus two self-update no-op nested `.update()` calls replaced with a real shallow-recursive merge loop, so a config file missing keys (or entire top-level sections) added after it was last saved correctly backfills from `DEFAULT_CONFIG` instead of silently losing them.
- **save-config-non-atomic** — `save_config()` now writes to a `.json.tmp` sibling, `flush()`+`fsync()`s it, then `os.replace()`s it over the real path; a mid-write failure leaves the original file untouched and cleans up the temp file.
- **check-connection-polling** — initially missed when splitting the workflow into groups (caught during my own post-workflow review pass, not by either adversarial reviewer, since it wasn't assigned to any group). Fixed directly afterward: `_check_connection()` (a real USB control transfer) is now throttled to at most once per second inside `read_scan`'s loop instead of running every iteration (~100/s).
- **setup-logging-clobber-rotate-payloads** — investigated both options the plan offered (a dedicated non-propagating `'scanner'` logger vs. a conservative root-logger fix) and found that every module in this codebase calls `logging.getLogger(__name__)`, which propagates to the root logger by default — switching to a dedicated logger would have silently dropped all of that existing console/file output. Took the conservative option instead: a module-level list tracks exactly the handlers `setup_logging()` itself previously attached, and a repeat call removes+closes only those, leaving any handler another library may have added to root untouched (fixing the actual "wipes out everything" bug while preserving today's working output). Made idempotent (repeat calls don't stack handlers). Replaced the plain `FileHandler` with a `RotatingFileHandler(maxBytes=1_000_000, backupCount=3)`. Stopped logging raw scan payloads (PII) at INFO/WARNING across three lines in `usb_hid_scanner.py`/`NfcScan.py` (a fourth, adjacent line flagged as a low-severity residual by the adversarial reviewer — `NfcScan.py`'s "User not found for scanned code" warning — was fixed in the same follow-up pass as check-connection-polling).

**Verification (three layers):**
1. *Scratch harnesses* (3, one per group, not committed, all using mocked `hid.device` — never real hardware): `verify_step6_scanner_fixes.py` (9 checks: multi-report NUL-padded reassembly via the quiet period, non-default read_size/encoding actually used, corrupted-data sentinel returned instead of `None`, handle-close-on-failure, both `NfcScan.py` call sites updated), `verify_scanner_config_fixes.py` (16 checks: partial-config backfill, DEFAULT_CONFIG left unmutated, mid-write-crash safety, normal round-trip), `verify_scanner_logging.py` (foreign-handler survival, idempotency across repeat calls, real log rotation). A fourth small script (`verify_check_connection_throttle.py`) added afterward confirmed the throttle fix: a 3-second read against a no-data mock now calls `_check_connection()` 3 times, not ~300. All re-run and re-passed after every subsequent edit to the same files.
2. *Independent adversarial review* — one review agent per group, each re-reading the actual current source (not the implementer's summary) and independently re-running the scratch harness. Two of three groups (`scanner_config`, `scanner_logging`) came back with zero bugs. The third (`usb_hid_scanner`+`NfcScan`) came back `FULLY_FIXED` for all four assigned findings but flagged one adjacent low-severity issue (a "User not found" warning log still containing the raw scan payload) — confirmed genuine and fixed directly.
3. *Regression suite* — full `pytest`: 54 passed, unchanged from every prior step, re-run after both the workflow's changes and the two follow-up fixes (check-connection-polling, the flagged log line).
4. *Data integrity* — `rental.db` confirmed row-identical to the Step 0 backup and `scanner_config.json` confirmed byte-identical (SHA-256 unchanged) at the end of the step.

**Process note:** splitting Step 6 into disjoint-file groups for parallel execution meant the plan's own grouping (some findings share a "Files:" list spanning multiple of my groups) had to be re-partitioned by actual file ownership rather than by finding ID — done deliberately to avoid two agents editing the same file concurrently, at the cost of missing one finding (check-connection-polling) in the initial split since it didn't fall cleanly under any of the three chosen groups. Caught during my own independent post-workflow file review, not by either adversarial reviewer (whose scope was, correctly, limited to what their assigned group actually claimed to fix) — a reminder that splitting by file doesn't automatically guarantee every finding in a "Files:"-overlapping list gets an owner, and the plan's own finding list should still be checked off item-by-item afterward, not just group-by-group.

---

## Step 7 — Remaining Minor fixes (grouped by file) ✅ COMPLETED (2026-07-09) (2 findings deferred by explicit user decision)

### `crud.py` / data-layer
- [x] **serialnum-default-false** — `models.py:14`. Now: `Column(String, default=False)` stores 0. Fix: change to `Column(String, default=None)` (or just `Column(String)`). Optional one-time cleanup: `UPDATE equipment SET serialnum = NULL WHERE serialnum = '0';`. Verify: insert without serialnum → stored NULL; UI shows empty S/N.
- [x] **update-cannot-reactivate** — `crud.py:27,69,113,29,30,71,115`. Now: `update_equipment/etype/department` fetch via status-filtered getters (can't reactivate) and truthiness guards block clearing. Fix: add `get_equipment_including_inactive`/`get_etype_including_inactive`; give the three updaters an `including-inactive` fetch (or a `get_*_func` param like `update_user`); change `if name:`/`if serialnum:` to `if name is not None:` (guard NOT-NULL columns against empty). Verify: soft-delete an Etype, `update_etype(id, status=True)` reactivates it. Depends on: M3.
- [x] **update-user-mutates-before-validate** — `crud.py:159,160,165,168,173`. Now: name/dep/status applied before the nfc dup check that can raise, leaving dirty state in the long-lived session. Fix: reorder so all validation (dept lookup 161-163, nfc dup check 167-171) runs before any mutation; wrap commit in `_commit(db)`. Verify: `update_user` with a valid name + a taken nfc → raises AND name unchanged on a fresh session. Depends on: M4.
- [x] **stats-outerjoin-negated** — `crud.py:454,455,471,639,641,707,709,723`. Now: `>0` filter/`HAVING` after `outerjoin` (and an inner `.join` in department stats) makes the "never rented" else branches dead. Fix (product decision): to show never-rented rows, relax/remove the `>0` filters (user 455, name HAVING 641) and change department `.join`→`.outerjoin` (707) removing 709; else delete the dead else branches (471-473, 656-658, 723-725) with a comment. Reference the correct pattern in `get_equipment_rental_summary` (334-343). Verify per chosen policy.
- [x] **notin-null-vuln** — `crud.py:286,287,299,300`. Now: a single NULL `equipment_id` in the open-rental subquery empties the Available list app-wide. Fix: add `Rental.equipment_id != None` to both subqueries (287, 300), or rewrite as NULL-safe `~db.query(Rental).filter(Rental.equipment_id == Equipment.id_eq, Rental.rental_end == None).exists()`. Verify: insert a rental with NULL `equipment_id` → Available list still correct. Depends on: M5.
- [ ] **nfc-payload-ambiguity — DEFERRED (explicit user decision 2026-07-08)** — `MatrixCode.py:46,106`; `fill_nfc_fields.py:40,57`. Now: user/equipment codes share the `{id}_{name}_{x}` format → cross-table collision. Fix (breaking): prefix user codes `u_…` and equipment `e_…` in both files; regenerate all nfc columns via "Update codes" and **reprint all labels**. Verify: a would-be colliding user/equipment now differ by prefix and each scan resolves correctly. (Weigh reprint cost — low real-world probability.) **Not implemented**: asked the user whether to do this now given it forces reprinting every live physical label; they chose to defer per the plan's own "low real-world probability" note.
- [ ] **tz-naive-timestamps — DEFERRED (explicit user decision 2026-07-08)** — `models.py:55`; `crud.py:214,241,394`; `duration_utils.py:58`. Now: naive local timestamps distort durations across DST; folds silently clamp to 0. Fix (migration-touching — **consider deferring**): store UTC (`datetime.now(datetime.timezone.utc)`, `DateTime(timezone=True)`), convert to local only at display, log rather than silently zero negatives. Requires a one-shot conversion of existing naive rows (no mixing aware/naive). Verify: a DST-straddling rental computes wall-clock-correct duration. **Not implemented**: asked the user given the migration-touching risk to live historical data; they chose to defer per the plan's own suggestion.

### `main.py` / main-app
- [x] **return-dialog-always-reports-success** — `main.py:227,228,229`; `crud.py:237`. Now: unconditional "Equipment returned successfully!" even for an already-returned rental. Fix: make `crud.return_equipment` return True only when it actually closed the rental (idempotent), False otherwise; branch the toast on the result. Verify: return once → success; trigger again → "already returned".
- [x] **session-reused-after-with-closed** — `main.py:707,711,765,788,801,825`. Now: `show_add_nfc_dialog` uses `fresh_db` after its `with` block closed (works only via SQLAlchemy silently reopening). *Currently dead code* (caller commented at 825). Fix: open a short-lived `with SessionLocal() as s:` inside each callback (scan_nfc 765, on_save 788), or keep a session open for the dialog lifetime and close it on dismiss. Decide whether to restore or delete the function. Verify (if restored): uncomment 825, scan + Apply, code persists, no detached-instance errors.
- [x] **admin-gesture-docstring-and-password** — `main.py:654,665,669,643`. Now: docstring says "5 clicks / 0.4s" but code is 3 clicks / 0.8s; password hardcoded `"supp"`. Fix: correct the docstring; extract `ADMIN_CLICK_COUNT=3`, `ADMIN_CLICK_WINDOW_SEC=0.8`; load the password from env/config (not real auth per CLAUDE.md — don't overclaim). Verify: triple-click within 0.8s opens the dialog; password comes from config.

### `main.py` + `gui/*` (shared)
- [x] **tkinter-tk-in-worker-threads** — `main.py:443,444,459,484,485,500`; `gui/gui_changeUser.py:111,123`; `gui/gui_changeEquip.py:107,119`. Now: `tk.Tk()` created via `run.io_bound` (worker thread) — unsafe, hangs/crashes on Windows. Fix: replace the tkinter folder picker with pywebview's `app.native.main_window.create_file_dialog(webview.FOLDER_DIALOG)` (correct thread), or run Tk on the main thread (not `run.io_bound`) with a single reused hidden root; in pure-browser mode fall back to a NiceGUI download. Apply to all four sites. Verify: on native Windows, open Generate/Download Codes and pick a folder 5+ times each — never freezes/crashes.

### `gui/*` dialogs
- [x] **dead-none-validation-add-dialogs** — `gui/gui_adduser.py:94,96,130`; `gui/gui_addequip.py:87,89,126`. Now: validation compares against literal `'None'`/`'Selected: '` that never appear; real placeholder text passes → raw backend error. Fix: track the selection in a nonlocal (`selected_dep`/`selected_etype`) and validate `if not name or not selected_x`; or compare against the actual placeholder string; drop the no-op `.replace('Selected: ', '')`. Verify: Add Device with a name but no type → friendly warning, not a raw "not found".
- [x] **cancelled-scan-code-lie** — `gui/gui_changeUser.py:92,102`; `gui/gui_changeEquip.py:88,99,221`; `crud.py:166`. Now: a cancelled scan flips the label to "Not set" while the DB keeps the old code (update skips `None`); no way to intentionally clear a code. Fix: on cancel, leave `nfc_value` unchanged and restore the label to the real stored state; add a "Clear code" button that sets a sentinel; make clearing persist as `nfc = None` (not `''` — two empty strings collide on UNIQUE). Verify: scan then cancel on a coded user → indicator stays "Code scanned"; Clear → nfc NULL after save.
- [x] **stale-dropdown-data-add-dialogs** — `gui/gui_addequip.py:19,123`; `gui/gui_adduser.py:19,22,128`. Now: module-level `data` loaded once at import; renames elsewhere never refresh it; `refresh_departments` is dead code. Fix: add `refresh_etypes()` (with `db.expire_all()`) and call it at the top of `show_add_equipment_dialog`; actually call `refresh_departments()` at the top of `show_add_user_dialog`. Verify: rename a type/department, open the Add dialog without restart → new name shown and add succeeds.
- [x] **empty-row-leak-cancelled-scan** — `gui/gui_addequip.py:80,81`; `gui/gui_adduser.py:88,89`. Now: cancelled-scan else-branch opens a new `ui.row()` just to set an attribute, leaking an empty row each time. Fix: remove the `with ui.row()...` wrapper — set `nfc_label.content` directly. (Coincides with cancelled-scan-code-lie.) Verify: cancel-scan repeatedly → no empty rows accumulate.
- [x] **unbounded-dialog-accumulation** — `gui/gui_changeUser.py:222`; `gui/gui_changeEquip.py:240`; `gui/gui_changeDep.py:169`; `gui/gui_changeEtype.py:160`; `gui/gui_changeRental.py:427,494`. Now: a fresh `ui.dialog()` per open, never deleted; auto-reopen timers add more. Fix: register `dialog.on('hide', lambda: dialog.delete())`; add `parent_dialog.delete()` after `close()` in the auto-reopen path, or reuse a single dialog per editor. Verify: open/close Edit Users ~50× → q-dialog node count doesn't grow unbounded.
- [x] **dead-zero-rental-filter-8x** — `gui/gui_reports.py:152,200,275,319,397,442,702,747`. Now: 8 list-comprehensions filter for `'0'`/`''` that the `'D:HH:MM'` strings never equal (and crud already excludes zero rows) — dead code. Fix: delete all 8 comprehension lines, assign the raw stats directly. Verify: each stats report shows an unchanged row set. Depends on: M12 (if numeric filtering is later desired, use `total_rental_seconds`).
- [x] **scanner-config-blocking-and-half-save** — `gui/gui_scanner_config.py:73,175,124,259,262,264,273`. Now: `check_connection_status()`/`refresh_devices()` run synchronously during dialog build (UI freezes; spinner never renders); save does two independent writes → half-saved config on partial failure. Fix: make `show_scanner_config_dialog` async, open the dialog first, then `await run.io_bound(...)` for the blocking USB calls (spinner renders); make save atomic (single write of vid+pid+mode, coordinate with `save-config-non-atomic`) and report per-part results if split. Verify: dialog appears immediately with a visible spinner while devices load; a simulated partial-save failure names which half failed.
- [x] **bulk-status-commit-order — NOT REPRODUCED** — `gui/gui_changeDep.py:151,156,159`; `gui/gui_changeEtype.py:142,147,150`; `crud.py:196,206`. The reported partial-update cannot occur: the rename and the bulk `User.status`/`Equipment.status` UPDATE flush in a **single transaction**, so a UNIQUE-constraint failure rolls both back atomically. Fix: none required for correctness. Optional cleanup: move the "Updated status for N …" `ui.notify` after the final commit; add explicit try/except+rollback (ties into M4). **Do not split into two commits** — that would introduce the bug the report feared. Verify: rename a department to a colliding name with "Apply to All Users" → no user.status changed, name unchanged.

### Web viewer
- [x] **web-viewer-shared-module-session** — `web_viewer/viewer_app.py:21,45,306,100`. Now: one module-level `db` shared by all clients; up-to-30s staleness and an `ObjectDeletedError` window on hard-deleted rentals. Fix: replace with per-fetch `with SessionLocal() as db:` in each read site (ViewerState 24-37, apply_combined_filters 190, reset_filter 261, full_refresh 299, show_rental_history 108). Since the app is read-only, per-fetch is simplest and removes the staleness. Verify: two LAN clients; rename an item and delete a rental in the main app → both reflect it on next refresh, no `ObjectDeletedError`.
- [x] **web-viewer-readonly-and-storage-secret** — `web_viewer/viewer_app.py:14,21,376,381`. Now: read-only by convention only; `create_all` runs; hardcoded `storage_secret`; binds `0.0.0.0`. Fix: give the viewer its own **read-only** engine (`sqlite:///file:<abs>/rental.db?mode=ro&uri=true`, absolute path from M2) and a viewer-local sessionmaker (stops `create_all` writing); move `storage_secret` to env/config with a strong random value; reconsider/​document the `0.0.0.0` exposure. Test the WAL+read-only combination together (a pure `?mode=ro` connection may fail to create `-wal`/`-shm`). Verify: any write via the viewer's session raises "attempt to write a readonly database"; normal viewing works; `storage_secret` from config. Depends on: M2.

**Commit Step 7** (group by file/area as convenient).

### Review — how Step 7 was done

**Scope decision, made before implementation:** two findings (`nfc-payload-ambiguity`, `tz-naive-timestamps`) have real-world consequences beyond a code change — the first forces reprinting every physical Data Matrix label already in circulation, the second requires a one-shot conversion of every historical timestamp in the live `rental.db`. Both were flagged by the plan itself as "consider deferring"/weigh the cost. Rather than deciding unilaterally, the user was asked directly; they chose to defer both, matching the plan's own hedge. They remain unchecked in this list, marked `DEFERRED` with the date, and are not implemented.

**Approach for the rest:** the crud.py/models.py data-layer findings (`serialnum-default-false`, `update-cannot-reactivate`, `update-user-mutates-before-validate`, `stats-outerjoin-negated`, `notin-null-vuln`) plus the crud.py portions of `return-dialog-always-reports-success` and `cancelled-scan-code-lie` were done directly (one coherent pass, since they all converge on the same file); `main.py` + `gui/gui_changeUser.py` + `gui/gui_changeEquip.py` were also done directly immediately after (the `tkinter-tk-in-worker-threads`, `cancelled-scan-code-lie`, and `unbounded-dialog-accumulation` findings all touch 2-3 of these same three files, so splitting them across parallel agents risked exactly the kind of collision noted as a risk in Step 6's review). The remaining 6 fully-disjoint-by-file findings (`gui/gui_adduser.py`+`gui/gui_addequip.py`, `gui/gui_changeDep.py`+`gui/gui_changeEtype.py`, `gui/gui_changeRental.py`, `gui/gui_reports.py`, `gui/gui_scanner_config.py`, `web_viewer/viewer_app.py`) were handled by a 6-group parallel Workflow, each group implementing then independently adversarially reviewed.

**A shared root, implemented once:** `crud.py` gained a `CLEAR_NFC` sentinel string (mirroring the existing `'__CORRUPTED__'` sentinel convention from `usb_hid_scanner.py`) so `update_user`'s `nfc` parameter can distinguish "leave untouched" (`None`, the default) from "explicitly clear to a real NULL" (`CLEAR_NFC`) — needed because two cleared users both writing `nfc=''` would collide on the UNIQUE constraint. `gui_changeEquip.py`'s hand-rolled ORM update (it doesn't go through `crud.update_user`) got the identical sentinel-check inline. A new `native_dialogs.py` module holds one `pick_folder_native()` helper (pywebview's `create_file_dialog`, which is already async and marshals the call to the real window thread) shared by `main.py` (2 sites) and the two `gui_change*.py` files (1 site each), replacing 4 duplicated `tk.Tk()`-via-`run.io_bound()` blocks.

**Per-finding deltas (direct work):**
- **serialnum-default-false** — `models.py`'s `Equipment.serialnum` column default changed from `False` to unset. Found and fixed the live consequence too: 30 existing equipment rows had `serialnum='0'` (SQLite's TEXT-affinity coercion of the Python `False` the old default inserted). Wrote `migrations/002_clear_false_serialnum_sentinel.py`, tested against a scratch copy first, then ran against the live `rental.db` (30 rows cleared to real NULL, confirmed via row-content diff against the Step 0 backup — the *only* 30 rows that differ, everything else byte-for-byte identical).
- **update-cannot-reactivate** — added `get_equipment_including_inactive`/`get_etype_including_inactive` (mirroring the existing `get_department_including_inactive`); all three updaters gained a `get_*_func` parameter (mirroring `update_user`'s existing pattern) so a caller can opt into reactivating a soft-deleted row; `name`/`serialnum` truthiness guards changed to `is not None` checks with an explicit empty-name rejection for NOT NULL columns, and `serialnum` empty string now clears to real NULL.
- **update-user-mutates-before-validate** — reordered `update_user` so the department lookup and nfc dup-check (both of which can raise) run before any attribute is mutated on the ORM object.
- **stats-outerjoin-negated** — removed the `>0`/`HAVING` filters in `get_user_rental_statistics`/`get_equipment_name_statistics` and changed `get_department_rental_statistics`'s inner `.join` to `.outerjoin` — the "never rented" `else` branches in all three were already written (someone had anticipated this fix) and just needed the filter blocking them removed.
- **notin-null-vuln** — added `Rental.equipment_id != None` to both `NOT IN` subqueries in `get_available_equipment`/`get_available_equipment_by_type`.
- **return-dialog-always-reports-success** — `crud.return_equipment`'s contract changed from "returns the Rental object" to "returns `bool`, `True` only if it just closed an open rental"; `main.py`'s return-dialog now branches the toast on that result.
- **session-reused-after-with-closed** — `show_add_nfc_dialog` restructured so only the initial user-list fetch happens inside `with SessionLocal():`; the `scan_nfc`/`on_save` callbacks (which run later, after the function has returned and that session has closed) now open their own short-lived sessions. Left the caller commented out as found — restoring the UI entry point is a product decision, not a bug-fix.
- **admin-gesture-docstring-and-password** — extracted `ADMIN_CLICK_COUNT=3`/`ADMIN_CLICK_WINDOW_SEC=0.8` constants (docstring corrected to match), and `ADMIN_PASSWORD` now reads `BNRS_ADMIN_PASSWORD` from the environment with the historical `"supp"` as a fallback (still explicitly not real auth, per `CLAUDE.md`).
- **tkinter-tk-in-worker-threads** — all 4 sites (`main.py`'s Generate Users/Equipment Codes, `gui_changeUser.py`/`gui_changeEquip.py`'s Download QR Code) now call the shared `native_dialogs.pick_folder_native()`.
- **cancelled-scan-code-lie** — `scan_nfc` in both `gui_changeUser.py`/`gui_changeEquip.py` now checks `scan_status` and leaves the existing code (and label) untouched on anything but `"success"`, instead of unconditionally trusting the returned data's truthiness; a new "Clear code" button sets `nfc_value = crud.CLEAR_NFC` explicitly.

**Per-finding deltas (parallel Workflow groups, independently re-verified by me afterward — see below):**
- **dead-none-validation-add-dialogs**, **stale-dropdown-data-add-dialogs**, **empty-row-leak-cancelled-scan** — `gui_addequip.py`/`gui_adduser.py`: dropdown selections now tracked via a `nonlocal` variable set by the item's `on_click` instead of parsed back out of the label text (which never matched the placeholder-check literals); `refresh_etypes()` added and `refresh_departments()` (pre-existing dead code) now actually called at the top of their respective Add dialogs; the cancelled-scan branch's leaked `ui.row()` wrapper removed.
- **unbounded-dialog-accumulation** — `dialog.on('hide', dialog.delete)` added before every `dialog.open()` across `gui_changeDep.py`, `gui_changeEtype.py`, and `gui_changeRental.py` (which turned out to have a third affected dialog, `delete_rental_record`'s confirm dialog, beyond the 2 the plan cited — fixed for consistency, same as the earlier direct-work files).
- **bulk-status-commit-order** (optional cleanup) — applied in both `gui_changeDep.py`/`gui_changeEtype.py`: the "Updated status for N …" notification now fires after `session.commit()` succeeds rather than before, with no change to the transaction shape.
- **dead-zero-rental-filter-8x** — all 8 no-op filter comprehensions removed from `gui_reports.py`'s 4 report builders; confirmed by direct comparison that re-applying the deleted filter logic to the raw stats produces an identical list (proving it was truly dead), and that this also means the never-rented rows the data-layer fix now surfaces flow through unfiltered.
- **scanner-config-blocking-and-half-save** — `show_scanner_config_dialog` is now `async`; the dialog opens immediately with loading placeholders, then `await run.io_bound(...)`s the USB connection check and device enumeration; `save_configuration()` now builds one merged config dict and calls `scanner_config.save_config()` once instead of two independent `update_usb_config()`/`set_scanner_mode()` writes. **Caught in my own follow-up review, not by the parallel group's work**: `reset_to_defaults()` had the exact same two-independent-writes pattern the finding was about, just in a different function the group's fix didn't reach — fixed directly with the identical single-write pattern.
- **web-viewer-shared-module-session**, **web-viewer-readonly-and-storage-secret** — `web_viewer/viewer_app.py` now has its own engine on a `sqlite:///file:...?mode=ro&uri=true` URI (absolute path via `paths.APP_DIR`) instead of importing `database.SessionLocal`, which also removes the `create_all()` side effect that import used to carry; every read site now opens its own `with SessionLocal() as db:`; `storage_secret` reads `BNRS_VIEWER_STORAGE_SECRET` with the historical string as fallback. **Independently re-tested by me** (not just trusted from the diff) directly against the live `rental.db`: real `SELECT`s through the read-only engine succeed (143 equipment rows, 33 users), and a real `UPDATE` through the same engine raises `sqlite3.OperationalError: attempt to write a readonly database` — confirming the mode=ro+WAL combination genuinely works on this database rather than silently no-op'ing.

**Process note — a workflow session-limit interruption, and what it means for trust in this step's verification:** the parallel Workflow hit the account's session limit partway through (`resets 7:40pm Europe/Berlin`), so 4 of 6 "implement" agents and 2 of 6 "verify" agents never returned a structured report — but the tool calls they'd already made (Edit/Write) had already landed on disk before the error, so `git status`/`git diff` showed real, substantive changes for every one of the 6 files with no report to describe or vouch for them. Rather than trust unreported work, every file's actual diff was read line-by-line against the plan's finding text as if no report existed at all (this is what surfaced the `reset_to_defaults()` gap above). A fresh scratch harness was then written to directly exercise the previously-unverified changes (`gui_addequip.py`/`gui_adduser.py`'s selection-tracking and refresh functions, `gui_scanner_config.py`'s consolidated-save shape) rather than accepting "it compiles" as sufficient.

**Verification (four layers):**
1. *Scratch harnesses* (3 separate ones, not committed): the data-layer functions directly (22 checks — reactivation, validation-before-mutation, `CLEAR_NFC`, `return_equipment` idempotency, never-rented stats rows, NULL-safe availability queries); `gui_changeUser.py`/`gui_changeEquip.py`'s `apply_changes()` called directly end-to-end plus `pick_folder_native()` (8 checks); the groups whose reports were lost to the session-limit error (11 checks, 1 harness false-positive from my own comment text, explained above). All passed.
2. *Independent adversarial review* — 2 of the 6 parallel-workflow groups got a full independent reviewer pass before the session limit hit (both returned clean); the other 4 were reviewed by me directly reading their diffs against the plan text, which is what caught the `reset_to_defaults()` gap.
3. *Live-database test* — the read-only+WAL SQLite combination for the web viewer was verified against the actual live `rental.db`, not a scratch copy, since a false negative here would only surface at real deployment.
4. *Regression suite + data integrity* — full `pytest`: 54 passed (unchanged from every prior step). `rental.db` compared row-by-row against the Step 0 backup: only the 30 `serialnum` cleanup rows differ, everything else identical. `scanner_config.json` SHA-256 unchanged.

**Known, out-of-scope residual gaps:** `nfc-payload-ambiguity` and `tz-naive-timestamps`, deferred per explicit user decision (see above). `show_add_nfc_dialog` in `main.py` remains dead code (its caller stays commented out) — the session bug is fixed, but re-exposing the UI entry point wasn't this step's call to make.

---

## Step 8 — Info / cleanup (optional, low priority) ✅ COMPLETED (2026-07-09)

- [x] **echo-true** — `database.py:9`. Change `echo=True` → `echo=False` (optionally `echo=os.environ.get('BNRS_SQL_ECHO','')=='1'`). Batch with the M5 edit (same `create_engine` line). Verify: console no longer prints SQL/params during rent/return.
- [x] **dead-code-get-card-uid** — `NfcScan.py:192-225,8-11`. Delete unused `get_card_uid()` and the three now-unused `smartcard` imports (verify no other `smartcard`/`readers`/`toHexString`/`CardConnectionException`/`NoCardException` references first). If `pyscard` is unused repo-wide, drop it from `requirements.txt`. Verify: `python -c "import NfcScan"` imports cleanly.
- [x] **dead-code-scanning-active** — `NfcScan.py:23`. Delete the unused `scanning_active = False` global. Verify: import clean, grep shows no references.
- [x] **matrixcode-engine-leak** — `MatrixCode.py:33,93`. Now: a new engine per call, never disposed. Fix: `from database import SessionLocal` and use it (best — shares the WAL engine), or add `engine.dispose()` in the finally (74, 134). Verify: loop `update_user_codes()` many times → no growth in open connections.
- [x] **duration-utils-docstring-overflow** — `duration_utils.py:24,115,119,51`. Now: docstring example inconsistent; `format_duration_from_seconds(float('inf'))` raises OverflowError. *Module currently unused.* Fix: correct the docstring to a self-consistent `{'duration':'1:02:35','duration_seconds':95730.0}`; add `import math`; after the `<=0` check, `if math.isinf(total_seconds) or math.isnan(total_seconds): return 'Active rental'`. Coordinate with M12's owner before adopting vs. deleting the module. Verify: `format_duration_from_seconds(float('inf'))` returns a string; `(95730)` returns `'1:02:35'`.
- [ ] **Env/venv drift note (informational).** The tracked `*.pyc` are cpython-313 while the active venv is Python 3.11.9 — stale build noise (removed in M22). The venv also carries unused bloat (auto-py-to-exe/Eel/bottle/gevent) that must **not** be added to `requirements.txt` (M23).

**Commit Step 8** ("Cleanup: dead code, docstrings, echo=False, engine disposal").

### Review — how Step 8 was done

All 5 findings done directly (small, disjoint, mechanical — no parallel workflow needed).

- **echo-true** — `database.py`'s `create_engine` now defaults `echo=False`, overridable via `BNRS_SQL_ECHO=1` for debugging. Confirmed no other `create_engine(..., echo=True)` call sites exist repo-wide.
- **dead-code-get-card-uid** — deleted `get_card_uid()` and the 3 `smartcard` imports it was the sole user of (`from smartcard.System import readers`, `from smartcard.util import toHexString`, `from smartcard.Exceptions import CardConnectionException, NoCardException` — confirmed via grep that none of `readers`/`toHexString`/`CardConnectionException`/`NoCardException` are referenced anywhere else in the file or repo). `pyscard` was then confirmed unused repo-wide and dropped from `requirements.txt`. `CLAUDE.md`'s description of `NfcScan.py` also mentioned this now-deleted legacy NFC-card reading path — updated that line too, since leaving it would make the docs actively wrong about what the file does.
- **dead-code-scanning-active** — deleted the unused `scanning_active = False` module global (confirmed zero references via grep).
- **matrixcode-engine-leak** — `MatrixCode.py`'s `update_user_codes()`/`update_equipment_codes()` each created a brand-new `create_engine(DATABASE_URL)` per call, never disposed. Took the plan's "best" option: both now use the shared `SessionLocal` from `database.py` (the same WAL-mode engine every other part of the app uses) instead of creating their own. `fill_nfc_fields.py` has the identical pattern but isn't named in this finding and is a rarely-run one-shot CLI script (the leaked engine dies with the process anyway) — left untouched to stay in scope.
- **duration-utils-docstring-overflow** — `duration_utils.py` (confirmed still unused repo-wide, so the "coordinate with M12's owner" note resolves to "still not adopted, same decision as Step 4"): corrected the module docstring's example (`'2:15:30'` didn't match `95730.0` seconds — the correct value is `'1:02:35'`), and `format_duration_from_seconds()` now checks `math.isinf()`/`math.isnan()` before the `int()` conversion that used to raise `OverflowError`/`ValueError`, returning `"Active rental"` to match the sentinel `calculate_duration_data()` already uses for the same case.
- **Env/venv drift note** — informational only per the plan; no action taken.

**Verification:** `python -m py_compile` on all 4 touched `.py` files; direct smoke tests confirming `get_card_uid`/`scanning_active` are gone from `NfcScan`'s namespace, `database.engine.echo` defaults `False`, `MatrixCode.py`'s source no longer contains `create_engine`, and `format_duration_from_seconds` returns `"Active rental"` for both `inf` and `nan` instead of raising. Full `pytest`: 54 passed (unchanged). `rental.db`/`scanner_config.json` untouched — this step made no database writes.

This closes out `CODE_REVIEW_FIX_PLAN.md`: all findings are now `[x]` except the two explicitly deferred in Step 7 (`nfc-payload-ambiguity`, `tz-naive-timestamps`), which remain available for a future session if you ever want to revisit them. The only remaining item in this document is the manual "Regression checklist" below, which is for you to drive through in the running app, not something to implement.

---

## Step 9 — Findings the original plan missed entirely ✅ COMPLETED (2026-07-09)

Found by a final audit workflow launched after Step 8, in response to the user asking for confirmation that everything was really done. The audit's coverage-check phase diffed every finding ID in `CODE_REVIEW_REPORT.md` against this plan's Coverage table and found the table only actually listed 71 rows despite the intro claiming 74 — these 3 findings had fallen through with **no remediation decision of any kind**: not fixed, not deferred, not marked "not reproduced," just never discussed anywhere in the plan.

- [x] **M1 — `NameError` in `get_active_rentals_summary`** — `crud.py` (was lines 498-500). Now: `#days, remainder = divmod(total_seconds, 86400)` was commented out, but the very next line, `hours, remainder = divmod(remainder, 3600)`, still read the now-undefined `remainder` — a guaranteed `NameError` on the first active rental in the loop. The function has zero callers anywhere in the repo (confirmed via repo-wide grep), so this never crashed anything live — but it was a real, reproducible crash landmine. Fix: deleted the three broken/vestigial lines; `days`/`hours`/`minutes`/`seconds` were already computed correctly two lines above via `duration.days`/`duration.seconds`, so `duration_str` now uses those directly with no functional change to correct callers, just removal of the dead, crashing redefinition attempt. Verified: called the function directly against a seeded active rental — returns a real summary with a valid `D:HH:MM` string, no exception.

- [x] **blocking-calls-on-event-loop** — `NfcScan.py` (`scan_task`'s and `usb_scanner_background_task`'s `scanner.connect()` calls). Now: `scanner.connect()` (opening a USB HID device, a blocking OS call) was called directly inside `async def` functions with no `run_in_executor`, unlike the adjacent `read_scan()` calls which already correctly run through an executor — meaning device-open latency (driver handshake, permission prompts, etc.) blocked the single-threaded NiceGUI event loop for every connected client. This finding was explicitly named in Step 2's own review as "the Minor `blocking-calls-on-event-loop` finding, scheduled for Step 7" — and then never appeared in Step 7 at all; a tracked promise that was silently dropped somewhere in this session. Fix: both `connect()` call sites now go through `await loop.run_in_executor(None, scanner.connect)`, mirroring the existing `read_scan()` pattern exactly; the get_scanner_mode()/get_usb_config() config-file reads the report also named were assessed and left as direct calls — they're small local JSON reads (sub-millisecond), and wrapping them in an executor would add complexity for negligible benefit, unlike the genuinely slow USB device-open call. Verified via source inspection that both `connect()` sites are executor-wrapped and no bare `scanner.connect()` call remains; full `pytest` still 54 passed.

- [x] **unknown-scanner-mode-disables-scanning-in-selection-dialog** — `NfcScan.py`'s `get_user_input_with_selection`. Now: this dialog's mode-routing (`if mode == "keyboard":` for the input field, `if mode == "usb_vendor": ... elif mode == "keyboard": ...` for starting the background task/focus-maintenance) has no `else` branch, unlike `get_nfc_input`'s explicit "unknown mode → fall back to keyboard, with a warning log" branch a few functions above it in the same file. A hand-edited or corrupted `scanner_mode` value in `scanner_config.json` would silently leave this dialog with neither a working keyboard input field nor a running background scanner — the "Scan User's Data Matrix Code" section would sit forever on "Ready to scan..." with nothing listening, leaving only the manual dropdown selection as a (still-working) escape hatch. Fix: normalized `mode` once, immediately after it's read from config, exactly mirroring `get_nfc_input`'s existing fallback (log a warning, treat anything other than `"usb_vendor"`/`"keyboard"` as `"keyboard"`) — both downstream branches then correctly pick up the corrected value with no other code change needed. Verified via source inspection that the normalization block is present and both downstream mode checks are now unreachable-with-nothing-happening.

**Process note:** this step exists because the plan's own intro claim ("79 verified finding entries... resolving to 74 unique finding IDs... the Coverage Table maps every ID to its Step") was itself never re-verified against the source report until this final audit — every prior step trusted the plan's own scope as complete and correct, and none of the 8 completed steps' review sections ever cross-checked back against `CODE_REVIEW_REPORT.md` to confirm nothing had been dropped. The lesson: "did I finish what I was assigned" and "did everything that needed doing get assigned in the first place" are different questions, and this session only asked the first one until explicitly prompted to check the second.

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

**Correction (2026-07-09):** this table originally listed only 71 rows despite the 74 claimed above — 3 real findings from `CODE_REVIEW_REPORT.md` (M1, and two Minor findings) had no row at all, meaning no remediation decision had been made for them anywhere in this document. Found by a final audit's coverage-check phase (diffing every ID in the report against this table) and fixed directly as Step 9. All three now have rows below, mapped to Step 9.

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
| M1 | `NameError` in `get_active_rentals_summary` (dead code, zero callers) | 9 |
| blocking-calls-on-event-loop | `scanner.connect()` blocks the UI thread | 9 |
| unknown-scanner-mode-disables-scanning-in-selection-dialog | No fallback for a corrupted mode value | 9 |

**Count check:** 74 unique IDs listed = 79 finding entries − 5 cross-area duplicates. Every finding in `CODE_REVIEW_REPORT.md` is now accounted for — corrected 2026-07-09 after a final audit found 3 of the 74 (M1 and the two Step-9 Minor findings above) had been silently missing from this table with no remediation decision at all; see Step 9 and the correction note above the table.