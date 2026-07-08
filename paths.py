"""
Application directory anchor (M2, CODE_REVIEW_FIX_PLAN.md Step 3).

`database.py`, `scanner_config.py`, and `scanner_logging.py` all need the same
frozen-aware "where does this app actually live" directory, but must not
depend on each other (scanner_config/scanner_logging are imported by the test
suite in isolation and must not trigger database.py's engine/create_all side
effects). This module has no other imports so any of them can use it safely.
"""
import sys
from pathlib import Path

APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
