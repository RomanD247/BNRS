import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from models import Base
from paths import APP_DIR

# SQLite database URL, anchored to the application directory (not the launch
# CWD) so running from a different folder can't create/read the wrong DB.
DATABASE_URL = "sqlite:///" + (APP_DIR / "rental.db").as_posix()

# One-file frozen builds unpack bundled data into a temp _MEIPASS dir; seed
# APP_DIR with the bundled DB on first run if no live DB exists there yet.
if getattr(sys, "frozen", False) and not (APP_DIR / "rental.db").exists():
    bundled_db = Path(getattr(sys, "_MEIPASS", "")) / "rental.db"
    if bundled_db.exists():
        shutil.copy(bundled_db, APP_DIR / "rental.db")

# Creating a DB Engine
engine = create_engine(DATABASE_URL, echo=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, conn_record):
    """WAL + busy_timeout let the main app and the read-only web viewer share
    rental.db without "database is locked" errors (M5); foreign_keys=ON turns
    on FK enforcement now that the live DB has been confirmed orphan-free."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


# Creating a Session Factory
SessionLocal = sessionmaker(bind=engine)

# Creating tables in a database
Base.metadata.create_all(bind=engine)
