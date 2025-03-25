from sqlalchemy.orm import Session
from models import Equipment, User, Rental
from typing import List, Optional
import datetime

# Equipment CRUD operations
def create_equipment(db: Session, name: str, artnum: str = None, etype: str = None) -> Equipment:
    """Create new equipment"""
    equipment = Equipment(name=name, artnum=artnum, etype=etype)
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment

def get_equipment(db: Session, equipment_id: int) -> Optional[Equipment]:
    """Get equipment by ID"""
    return db.query(Equipment).filter(Equipment.id_eq == equipment_id).first()

def get_all_equipment(db: Session) -> List[Equipment]:
    """Get all equipment"""
    return db.query(Equipment).all()

def update_equipment(db: Session, equipment_id: int, name: str = None, 
                    artnum: str = None, etype: str = None) -> Optional[Equipment]:
    """Update equipment"""
    equipment = get_equipment(db, equipment_id)
    if equipment:
        if name: equipment.name = name
        if artnum: equipment.artnum = artnum
        if etype: equipment.etype = etype
        db.commit()
        db.refresh(equipment)
    return equipment

def delete_equipment(db: Session, equipment_id: int) -> bool:
    """Delete equipment"""
    equipment = get_equipment(db, equipment_id)
    if equipment:
        db.delete(equipment)
        db.commit()
        return True
    return False

# User CRUD operations
def create_user(db: Session, name: str, dep: str = None) -> User:
    """Create new user"""
    user = User(name=name, dep=dep)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id_us == user_id).first()

def get_all_users(db: Session) -> List[User]:
    """Get all users"""
    return db.query(User).all()

def update_user(db: Session, user_id: int, name: str = None, dep: str = None) -> Optional[User]:
    """Update user"""
    user = get_user(db, user_id)
    if user:
        if name: user.name = name
        if dep: user.dep = dep
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    """Delete user"""
    user = get_user(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

# Rental CRUD operations
def create_rental(db: Session, user_id: int, equipment_id: int) -> Rental:
    """Create new rental"""
    rental = Rental(user_id=user_id, equipment_id=equipment_id)
    db.add(rental)
    db.commit()
    db.refresh(rental)
    return rental

def get_rental(db: Session, rental_id: int) -> Optional[Rental]:
    """Get rental by ID"""
    return db.query(Rental).filter(Rental.id_re == rental_id).first()

def get_all_rentals(db: Session) -> List[Rental]:
    """Get all rentals"""
    return db.query(Rental).all()

def return_equipment(db: Session, rental_id: int) -> Optional[Rental]:
    """Return equipment (end rental)"""
    rental = get_rental(db, rental_id)
    if rental and not rental.rental_end:
        rental.rental_end = datetime.datetime.now()
        db.commit()
        db.refresh(rental)
    return rental

def get_active_rentals(db: Session) -> List[Rental]:
    """Get all active rentals (not returned)"""
    return db.query(Rental).filter(Rental.rental_end == None).all()

def get_user_rentals(db: Session, user_id: int) -> List[Rental]:
    """Get all rentals for a specific user"""
    return db.query(Rental).filter(Rental.user_id == user_id).all()

def get_equipment_renters(db: Session, equipment_id: int) -> List[User]:
    """Get all users who have rented specific equipment"""
    return db.query(User).join(Rental).filter(Rental.equipment_id == equipment_id).distinct().all()
