# models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()

class Equipment(Base):
    """Represents an equipment item that can be rented."""
    __tablename__ = "equipment"

    id_eq = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    artnum = Column(String, default=False)
    etype = Column(String, default=False)

class User(Base):
    """Represents a user who can rent equipment."""
    __tablename__ = "users"

    id_us = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    dep = Column(String, default=False) # department

class Rental(Base):
    """Represents an equipment rental event."""
    __tablename__ = "rentals"

    id_re = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id_us"))
    equipment_id = Column(Integer, ForeignKey("equipment.id_eq"))
    rental_start = Column(DateTime, default=datetime.datetime.now)
    rental_end = Column(DateTime, nullable=True)

    user = relationship("User")
    equipment = relationship("Equipment")
