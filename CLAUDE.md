# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**WenglorMEL Rental System** — a Windows desktop app for tracking internal equipment rentals (who has what, rent/return, history). Built with **NiceGUI** rendered as a native desktop window (via pywebview), backed by **SQLite** through **SQLAlchemy**. Equipment and users are identified by scanning **Data Matrix codes** with a USB scanner.

## Environment & commands

The active virtual environment is `bnrs/` (`bnrs_old/` is a stale copy — ignore it). Both are gitignored (never committed) and are treated as local vendored dependencies, not source.

```powershell
bnrs\Scripts\activate          # activate venv first
python main.py                 # run the app (opens native window on port 15716)
python web_viewer/viewer_app.py  # run the read-only network viewer alone (port 8585)
pip install -r requirements.txt
```

**Tests** live at the repo root as `test_*.py`. They run two ways — most have `if __name__ == "__main__"` blocks and print their own pass/fail, and several also work under pytest (the `test_property_*.py` files use `hypothesis` for property-based testing):

```powershell
python test_property_mode_routing.py   # run one test as a script
pytest test_rental_workflow_integration.py   # or under pytest
pytest                                  # collect everything pytest-compatible
```

**Build** (PyInstaller, one-file windowed exe): `pyinstaller "WenglorMEL Rental System 2.1.5.spec"`. The spec bundles `rental.db`, `scanner_config.default.json` (a committed template — the live `scanner_config.json` is gitignored/local), the whole `nicegui` package, `web_viewer/`, and `libdmtx-64.dll` from pylibdmtx — the Data Matrix encoder fails silently without that DLL. Paths in the spec are portable (`SPECPATH`-relative), so it doesn't need editing per machine.

## Architecture

**Layered, with no web framework in the traditional sense** — NiceGUI builds the UI in Python and serves it to an embedded browser window.

- **[models.py](models.py)** — SQLAlchemy ORM. Six tables: `Equipment`, `Etype` (equipment type), `Department`, `User`, `Rental`, `Feedback`. Two conventions that pervade the codebase:
  - **Soft deletes**: rows carry a `status` boolean; "deleting" sets `status=False`. Every read query filters `status == True`. Never hard-delete.
  - **`nfc` column**: both `User` and `Equipment` have a unique `nfc` string. Despite the name, this now holds the **Data Matrix code payload**, not NFC data. This is the join key for scanning.
- **[database.py](database.py)** — creates the engine (`sqlite:///rental.db`, `echo=True` so all SQL prints to console) and `SessionLocal`. `Base.metadata.create_all` runs on import, so importing this module creates the DB.
- **[crud.py](crud.py)** — the entire data-access layer. All DB reads/writes go through here. Uses `joinedload` for eager relationship loading. Key scanner-facing functions: `find_equipment_by_nfc`, `find_user_by_nfc`, `is_equipment_rented`, `create_rental`, `return_equipment`.
- **[main.py](main.py)** — the app: the main screen (available vs. rented equipment lists, type/name filters, "Scan to Rent" button) and the **hidden admin panel**. On startup it also spawns `web_viewer/viewer_app.py` as a background subprocess and terminates it on exit.
- **[gui/](gui/)** — one module per admin dialog (`gui_addequip`, `gui_changeUser`, `gui_scanner_config`, …). `main.py` wires these into the admin panel; `gui/gui_reports.py` builds the report/history buttons.

### The scanner subsystem (the most active area of the code)

Scanning supports **two modes**, selected in `scanner_config.json` (`"scanner_mode": "usb_vendor" | "keyboard"`) and editable at runtime via the admin scanner-config dialog:

- `usb_vendor` — reads HID reports directly from the scanner in USB HID Vendor Mode (via `hidapi`). This is the default and the more robust path — it does not interfere with the keyboard focus.
- `keyboard` — legacy keyboard-wedge mode where the scanner types the code into a focused input.

Files:
- **[NfcScan.py](NfcScan.py)** — the central scanner + rental orchestration module (largest file). `get_nfc_input()` is the mode-routing entry point: it reads `scanner_mode` and dispatches to `get_usb_hid_input()` or `get_nfc_input_keyboard()`, returning a `(data, status)` tuple. `nfc_equipment_rental_workflow()` is the full scan-to-rent / scan-to-return flow. This file **also** generates the printable Data Matrix PNGs (via `pylibdmtx.encode`) and contains legacy NFC-card reading via `pyscard`.
- **[usb_hid_scanner.py](usb_hid_scanner.py)** — `USBHIDScanner` class: connect/disconnect, read & parse HID reports into a lowercase string.
- **[scanner_config.py](scanner_config.py)** — load/save/merge `scanner_config.json`, mode get/set, VID/PID validation. Default device is VID `4602` (0x11FA) / PID `33282` (0x8202).
- **[scanner_error_dialogs.py](scanner_error_dialogs.py)** / **[scanner_logging.py](scanner_logging.py)** — user-facing error dialogs and logging setup (writes `logs/scanner.log`).

### Data Matrix code identity scheme

Codes do **not** encode raw primary keys. [MatrixCode.py](MatrixCode.py) generates the `nfc` payloads from human-readable fields:
- User code = `{id_us}_{name}_{id_dep}` (lowercased)
- Equipment code = `{id_eq}_{name}_{serialnum}` (lowercased)

The admin panel's "update codes" buttons regenerate these into the `nfc` columns; the "generate codes" buttons in [NfcScan.py](NfcScan.py) render matching printable Data Matrix images. Scanning looks the payload up against the `nfc` column, so **changing a name/serialnum/department invalidates previously printed codes** — codes must be regenerated and reprinted.

### Web viewer

[web_viewer/viewer_app.py](web_viewer/viewer_app.py) is a **separate, read-only** NiceGUI app bound to `0.0.0.0:8585` for LAN access. It reads the same `rental.db` and cannot modify anything. `main.py` launches it automatically in the background. (Note: some older docs mention port 8081 — the code uses 8585.)

## Conventions & gotchas

- **Module-level sessions**: both `main.py` and `NfcScan.py` hold a long-lived `db = SessionLocal()`. Some dialogs deliberately open a fresh scoped session (`with SessionLocal() as fresh_db:`) to avoid stale data. When adding features that mutate then re-read, prefer a fresh session rather than the module-level one.
- **Admin access is a hidden gesture, not real auth**: clicking the invisible top-right button 3× within ~0.8s opens a password dialog. The password is hardcoded (`"supp"`, marked `#Change !password` in [main.py](main.py)). Do not treat this as security.
- **UI is async**: scanner reads and workflows are `async` NiceGUI handlers that `await` on `asyncio.Future`s resolved by dialog buttons. Follow the existing future-based dialog pattern rather than blocking calls.
- **The `.kiro/specs/` directory** holds feature specs (requirements/design/tasks) that drove past work; the many `TASK_*.md`, `USB_SCANNER_*.md`, and `*_SUMMARY.md` files at the root are implementation notes and user guides for the scanner rollout — useful context, not code.
- `rental.db` is committed and treated as the live database. Be careful — schema changes require migrating it (there is no migration framework; `create_all` only adds missing tables, not columns).
