from sqlalchemy.orm import Session
from models import Equipment, User, Rental, Department, Etype
from typing import List, Optional
import datetime

# Equipment CRUD operations
def create_equipment(db: Session, name: str, serialnum: str = None, etype: str = None) -> Equipment:
    """Create new equipment"""
    equipment = Equipment(name=name, serialnum=serialnum, etype=etype)
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
                    serialnum: str = None, etype: str = None) -> Optional[Equipment]:
    """Update equipment"""
    equipment = get_equipment(db, equipment_id)
    if equipment:
        if name: equipment.name = name
        if serialnum: equipment.serialnum = serialnum
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

# Etype CRUD operations
def create_etype(db: Session, name: str) -> Etype:
    """Create new equipment type"""
    etype = Etype(name=name)
    db.add(etype)
    db.commit()
    db.refresh(etype)
    return etype

def get_etype(db: Session, etype_id: int) -> Optional[Etype]:
    """Get equipment type by ID"""
    return db.query(Etype).filter(Etype.id_et == etype_id).first()

def get_etype_by_name(db: Session, name: str) -> Optional[Etype]:
    """Get equipment type by name"""
    return db.query(Etype).filter(Etype.name == name).first()

def get_all_etypes(db: Session) -> List[Etype]:
    """Get all equipment types"""
    return db.query(Etype).all()

def update_etype(db: Session, etype_id: int, name: str) -> Optional[Etype]:
    """Update equipment type"""
    etype = get_etype(db, etype_id)
    if etype:
        etype.name = name
        db.commit()
        db.refresh(etype)
    return etype

def delete_etype(db: Session, etype_id: int) -> bool:
    """Delete equipment type"""
    etype = get_etype(db, etype_id)
    if etype:
        db.delete(etype)
        db.commit()
        return True
    return False

# Department CRUD operations
def create_department(db: Session, name: str) -> Department:
    """Create new department"""
    department = Department(name=name)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department

def get_department(db: Session, department_id: int) -> Optional[Department]:
    """Get department by ID"""
    return db.query(Department).filter(Department.id == department_id).first()

def get_department_by_name(db: Session, name: str) -> Optional[Department]:
    """Get department by name"""
    return db.query(Department).filter(Department.name == name).first()

def get_all_departments(db: Session) -> List[Department]:
    """Get all departments"""
    return db.query(Department).all()

def update_department(db: Session, department_id: int, name: str) -> Optional[Department]:
    """Update department"""
    department = get_department(db, department_id)
    if department:
        department.name = name
        db.commit()
        db.refresh(department)
    return department

def delete_department(db: Session, department_id: int) -> bool:
    """Delete department"""
    department = get_department(db, department_id)
    if department:
        db.delete(department)
        db.commit()
        return True
    return False

# User CRUD operations
def create_user(db: Session, name: str, dep: str) -> User:
    """Create new user"""
    department = get_department_by_name(db, dep)
    if not department:
        raise ValueError(f"Department {dep} not found")
    
    user = User(name=name, id_dep=department.id)
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
        if dep:
            department = get_department_by_name(db, dep)
            if not department:
                raise ValueError(f"Department {dep} not found")
            user.id_dep = department.id
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

def get_available_equipment(db: Session) -> List[Equipment]:
    """Get all available equipment (not currently rented)"""
    # Get all equipment that either:
    # 1. Has no rentals at all
    # 2. Has only completed rentals (rental_end is not None)
    return db.query(Equipment).filter(
        ~Equipment.id_eq.in_(
            db.query(Rental.equipment_id).filter(Rental.rental_end == None)
        )
    ).all()
