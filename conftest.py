"""
Shared pytest fixtures for test isolation.

Two systemic problems this file fixes:
- Tests importing `database.SessionLocal` write to the live, committed
  `rental.db` (see CODE_REVIEW_FIX_PLAN.md finding C3). `db_session` gives
  every test its own throwaway SQLite file instead.
- Tests calling `scanner_config.set_scanner_mode`/`update_usb_config` rewrite
  the live `scanner_config.json` (finding C4). `isolated_scanner_config`
  redirects the module's `CONFIG_FILE` global to a temp file for the
  duration of every test, autouse so no test can opt out by omission.
"""

import os
import shutil
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import scanner_config
from models import Base, Department, Etype, User, Equipment
import crud


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test_rental.db"
    engine = create_engine(f"sqlite:///{db_file}", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        dep = Department(name="TestDep")
        session.add(dep)
        session.flush()
        et = Etype(name="TestType")
        session.add(et)
        session.flush()
        user = User(name="TestUser", id_dep=dep.id_dep, nfc="1_testuser_1", status=True)
        equip = Equipment(
            name="TestEquip",
            serialnum="SN1",
            etype_id=et.id_et,
            nfc="1_testequip_sn1",
            status=True,
        )
        # a second, already-rented unit so tests that need an existing open
        # rental (e.g. return-flow tests) don't have to skip on an empty DB
        rented_equip = Equipment(
            name="TestEquipRented",
            serialnum="SN2",
            etype_id=et.id_et,
            nfc="2_testequiprented_sn2",
            status=True,
        )
        session.add_all([user, equip, rented_equip])
        session.commit()
        crud.create_rental(session, user.id_us, rented_equip.id_eq, "Fixture seed rental")
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def isolated_scanner_config():
    original = scanner_config.CONFIG_FILE
    tmp = tempfile.mkdtemp()
    scanner_config.CONFIG_FILE = os.path.join(tmp, "test_scanner_config.json")
    try:
        yield
    finally:
        scanner_config.CONFIG_FILE = original
        shutil.rmtree(tmp, ignore_errors=True)
