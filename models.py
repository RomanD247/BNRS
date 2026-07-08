# models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()

class Equipment(Base):
    """Represents an equipment item that can be rented."""
    __tablename__ = "equipment"

    id_eq = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    serialnum = Column(String, default=False)
    etype_id = Column(Integer, ForeignKey("etypes.id_et"))
    status = Column(Boolean, default=True)
    etype = relationship("Etype", back_populates="equipments")
    nfc = Column(String, nullable=True, unique=True)

class Etype(Base):
    """Represents equipment type."""
    __tablename__ = "etypes"

    id_et = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    status = Column(Boolean, default=True)
    equipments = relationship("Equipment", back_populates="etype")

class Department(Base):
    __tablename__ = "departments"

    id_dep = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    status = Column(Boolean, default=True)
    users = relationship("User", back_populates="department")

class User(Base):
    """Represents a user who can rent equipment."""
    __tablename__ = "users"

    id_us = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    id_dep = Column(Integer, ForeignKey("departments.id_dep"))
    status = Column(Boolean, default=True)
    department = relationship("Department", back_populates="users")
    nfc = Column(String, nullable=True, unique=True)

class Rental(Base):
    """Represents an equipment rental event."""
    __tablename__ = "rentals"

    id_re = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id_us"))
    equipment_id = Column(Integer, ForeignKey("equipment.id_eq"))
    rental_start = Column(DateTime, default=datetime.datetime.now)
    rental_end = Column(DateTime, nullable=True)
    comment = Column(String, nullable=True)
    user = relationship("User")
    equipment = relationship("Equipment")

# DB-level backstop for M7 (app-layer guard is in crud.create_rental): at most
# one open (rental_end IS NULL) rental per piece of equipment. create_all only
# adds this to brand-new databases — the already-existing rental.db needs the
# one-off migrations/001_add_active_rental_unique_index.py script.
Index(
    "uq_active_rental_per_equipment",
    Rental.equipment_id,
    unique=True,
    sqlite_where=Rental.rental_end.is_(None),
)

class Feedback(Base):
    """Represents a feedback message."""
    __tablename__ = "feedback"

    id_fb = Column(Integer, primary_key=True)
    name = Column(String)
    date = Column(DateTime, default=datetime.datetime.now)
    feedback = Column(String, nullable=False)
