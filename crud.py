from sqlalchemy.orm import Session, joinedload
from models import Equipment, User, Rental, Department, Etype
from typing import List, Optional, Dict
import datetime
from sqlalchemy import func, case

# Equipment CRUD operations
def create_equipment(db: Session, name: str, serialnum: str = None, etype_id: int = None) -> Equipment:
    """Create new equipment"""
    equipment = Equipment(name=name, serialnum=serialnum, etype_id=etype_id, status=True)
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment

def get_equipment(db: Session, equipment_id: int) -> Optional[Equipment]:
    """Get equipment by ID"""
    return db.query(Equipment).options(joinedload(Equipment.etype)).filter(Equipment.id_eq == equipment_id, Equipment.status == True).first()

def get_all_equipment(db: Session) -> List[Equipment]:
    """Get all equipment"""
    return db.query(Equipment).options(joinedload(Equipment.etype)).filter(Equipment.status == True).all()

def update_equipment(db: Session, equipment_id: int, name: str = None, 
                    serialnum: str = None, etype_id: int = None, status: bool = None) -> Optional[Equipment]:
    """Update equipment"""
    equipment = get_equipment(db, equipment_id)
    if equipment:
        if name: equipment.name = name
        if serialnum: equipment.serialnum = serialnum
        if etype_id: equipment.etype_id = etype_id
        if status is not None: equipment.status = status
        db.commit()
        db.refresh(equipment)
    return equipment

def delete_equipment(db: Session, equipment_id: int) -> bool:
    """Soft delete equipment by setting status to False"""
    equipment = get_equipment(db, equipment_id)
    if equipment:
        equipment.status = False
        db.commit()
        return True
    return False

# Etype CRUD operations
def create_etype(db: Session, name: str) -> Etype:
    """Create new equipment type"""
    etype = Etype(name=name, status=True)
    db.add(etype)
    db.commit()
    db.refresh(etype)
    return etype

def get_etype(db: Session, etype_id: int) -> Optional[Etype]:
    """Get equipment type by ID"""
    return db.query(Etype).filter(Etype.id_et == etype_id, Etype.status == True).first()

def get_etype_by_name(db: Session, name: str) -> Optional[Etype]:
    """Get equipment type by name"""
    return db.query(Etype).filter(Etype.name == name, Etype.status == True).first()

def get_all_etypes(db: Session) -> List[Etype]:
    """Get all equipment types"""
    return db.query(Etype).filter(Etype.status == True).all()

def update_etype(db: Session, etype_id: int, name: str = None, status: bool = None) -> Optional[Etype]:
    """Update equipment type"""
    etype = get_etype(db, etype_id)
    if etype:
        if name: etype.name = name
        if status is not None: etype.status = status
        db.commit()
        db.refresh(etype)
    return etype

def delete_etype(db: Session, etype_id: int) -> bool:
    """Soft delete equipment type by setting status to False"""
    etype = get_etype(db, etype_id)
    if etype:
        etype.status = False
        db.commit()
        return True
    return False

# Department CRUD operations
def create_department(db: Session, name: str) -> Department:
    """Create new department"""
    department = Department(name=name, status=True)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department

def get_department(db: Session, department_id: int) -> Optional[Department]:
    """Get department by ID"""
    return db.query(Department).filter(Department.id_dep == department_id, Department.status == True).first()

def get_department_including_inactive(db: Session, department_id: int) -> Optional[Department]:
    """Get department by ID including inactive ones"""
    return db.query(Department).filter(Department.id_dep == department_id).first()

def get_department_by_name(db: Session, name: str) -> Optional[Department]:
    """Get department by name"""
    return db.query(Department).filter(Department.name == name, Department.status == True).first()

def get_all_departments(db: Session) -> List[Department]:
    """Get all departments"""
    return db.query(Department).filter(Department.status == True).all()

def update_department(db: Session, department_id: int, name: str = None, status: bool = None) -> Optional[Department]:
    """Update department"""
    department = get_department(db, department_id)
    if department:
        if name: department.name = name
        if status is not None: department.status = status
        db.commit()
        db.refresh(department)
    return department

def delete_department(db: Session, department_id: int) -> bool:
    """Soft delete department by setting status to False"""
    department = get_department(db, department_id)
    if department:
        department.status = False
        db.commit()
        return True
    return False

# User CRUD operations
def create_user(db: Session, name: str, dep: str) -> User:
    """Create new user"""
    department = get_department_by_name(db, dep)
    if not department:
        raise ValueError(f"Department {dep} not found")
    
    user = User(name=name, id_dep=department.id_dep, status=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).options(joinedload(User.department)).filter(User.id_us == user_id, User.status == True).first()

def get_user_including_inactive(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID including inactive ones"""
    return db.query(User).options(joinedload(User.department)).filter(User.id_us == user_id).first()

def get_all_users(db: Session) -> List[User]:
    """Get all users"""
    return db.query(User).options(joinedload(User.department)).filter(User.status == True).all()

def update_user(db: Session, user_id: int, name: str = None, dep: str = None, status: bool = None, get_user_func=get_user) -> Optional[User]:
    """Update user"""
    user = get_user_func(db, user_id)
    if user:
        if name: user.name = name
        if dep:
            department = get_department_by_name(db, dep)
            if not department:
                raise ValueError(f"Department {dep} not found")
            user.id_dep = department.id_dep
        if status is not None: user.status = status
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    """Soft delete user by setting status to False"""
    user = get_user(db, user_id)
    if user:
        user.status = False
        db.commit()
        return True
    return False

def get_all_users_including_inactive(db: Session) -> List[User]:
    """Get all users including inactive ones"""
    return db.query(User).options(joinedload(User.department)).all()

# Rental CRUD operations
def create_rental(db: Session, user_id: int, equipment_id: int, comment: str = None) -> Rental:
    """Create new rental"""
    rental = Rental(
        user_id=user_id, 
        equipment_id=equipment_id,
        rental_start=datetime.datetime.now(),
        comment=comment
    )
    db.add(rental)
    db.commit()
    db.refresh(rental)
    return rental

def get_rental(db: Session, rental_id: int) -> Optional[Rental]:
    """Get rental by ID"""
    return db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .options(joinedload(Rental.user).joinedload(User.department))\
        .filter(Rental.id_re == rental_id).first()

def get_all_rentals(db: Session) -> List[Rental]:
    """Get all rentals"""
    return db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .options(joinedload(Rental.user).joinedload(User.department))\
        .all()

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
    return db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .options(joinedload(Rental.user).joinedload(User.department))\
        .join(Equipment)\
        .filter(Equipment.status == True)\
        .filter(Rental.rental_end == None).all()

def get_user_rentals(db: Session, user_id: int) -> List[Rental]:
    """Get all rentals for a specific user"""
    return db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .filter(Rental.user_id == user_id).all()

def get_equipment_renters(db: Session, equipment_id: int) -> List[User]:
    """Get all users who have rented specific equipment"""
    return db.query(User)\
        .options(joinedload(User.department))\
        .join(Rental)\
        .filter(Rental.equipment_id == equipment_id).distinct().all()

def get_available_equipment(db: Session) -> List[Equipment]:
    """Get all available equipment (not currently rented)"""
    # Get all equipment that either:
    # 1. Has no rentals at all
    # 2. Has only completed rentals (rental_end is not None)
    return db.query(Equipment)\
        .options(joinedload(Equipment.etype))\
        .filter(Equipment.status == True)\
        .filter(
            ~Equipment.id_eq.in_(
                db.query(Rental.equipment_id).filter(Rental.rental_end == None)
            )
        ).all()

# New function to get equipment filtered by type
def get_available_equipment_by_type(db: Session, etype_id: int) -> List[Equipment]:
    """Get all available equipment of a specific type"""
    return db.query(Equipment)\
        .options(joinedload(Equipment.etype))\
        .filter(Equipment.etype_id == etype_id)\
        .filter(Equipment.status == True)\
        .filter(
            ~Equipment.id_eq.in_(
                db.query(Rental.equipment_id).filter(Rental.rental_end == None)
            )
        ).all()

# New function to get active rentals filtered by equipment type
def get_active_rentals_by_equipment_type(db: Session, etype_id: int) -> List[Rental]:
    """Get all active rentals for equipment of a specific type"""
    return db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .options(joinedload(Rental.user).joinedload(User.department))\
        .join(Equipment)\
        .filter(Equipment.etype_id == etype_id)\
        .filter(Equipment.status == True)\
        .filter(Rental.rental_end == None)\
        .all()

# --- New Function for Equipment Rental Summary ---
def get_equipment_rental_summary(db: Session) -> List[Dict]:
    """
    Get a summary for each piece of equipment including its type and total completed rental time.
    Calculates time based on completed rentals (rental_end is not None).
    """
    # Subquery to calculate total seconds for completed rentals per equipment_id
    # Using julianday for simplicity, might need adjustment for other DBs like PostgreSQL (use extract epoch)
    subquery = db.query(
        Rental.equipment_id,
        func.sum(
             (func.julianday(Rental.rental_end) - func.julianday(Rental.rental_start)) * 86400
        ).label("total_seconds")
    ).filter(Rental.rental_end != None)\
    .group_by(Rental.equipment_id)\
    .subquery()

    # Main query joining Equipment, Etype, and the subquery
    results = db.query(
        Equipment.name,
        Etype.name.label("etype_name"),
        subquery.c.total_seconds
    ).select_from(Equipment)\
    .join(Etype, Equipment.etype_id == Etype.id_et)\
    .filter(Equipment.status == True)\
    .outerjoin(subquery, Equipment.id_eq == subquery.c.equipment_id)\
    .order_by(Equipment.name)\
    .all()

    # Format results
    summary = []
    for name, etype_name, total_seconds_float in results:
        # Default text if no completed rentals were found for this item
        duration_str = "Never Rented / Only Active"
        if total_seconds_float is not None:
             total_seconds = int(total_seconds_float)
             if total_seconds > 0:
                # Convert seconds to a human-readable format (d h m s)
                days, remainder = divmod(total_seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_parts = []
                if days > 0: duration_parts.append(f"{days}d")
                if hours > 0: duration_parts.append(f"{hours}h")
                if minutes > 0: duration_parts.append(f"{minutes}m")
                # Show seconds if it's the only unit or total time is less than a minute
                if seconds > 0 or not duration_parts: duration_parts.append(f"{seconds}s")
                duration_str = " ".join(duration_parts)
             else:
                 # If total_seconds is 0, it means it was rented but for zero duration (or precision issues)
                 duration_str = "0s"

        summary.append({
            "equipment_name": name,
            "etype_name": etype_name,
            "total_rental_time": duration_str
        })

    return summary

# --- End of New Function ---

def get_active_rentals_summary(db: Session) -> List[Dict]:
    """
    Get a summary of all active rentals with user and equipment details.
    Returns data in format suitable for GUI table.
    """
    active_rentals = db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .options(joinedload(Rental.user).joinedload(User.department))\
        .join(Equipment)\
        .filter(Equipment.status == True)\
        .filter(Rental.rental_end == None).all()
        
    summary = []
    
    for rental in active_rentals:
        # Calculate duration of current rental
        duration = datetime.datetime.now() - rental.rental_start
        days = duration.days
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60
        
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60
        duration_str = f"{int(days)}:{int(hours):02}:{int(minutes):02}"
        
        summary.append({
            "equipment_name": rental.equipment.name,
            "equipment_type": rental.equipment.etype.name,
            "user_name": rental.user.name,
            "department": rental.user.department.name,
            "rental_start": rental.rental_start.strftime("%Y-%m-%d %H:%M:%S"),
            "current_duration": duration_str,
            "comment": rental.comment
        })
    
    return summary

def get_user_rental_statistics(db: Session, start_date=None, end_date=None) -> List[Dict]:
    """
    Get statistics for each user including their department and total rental time.
    Returns data in format suitable for GUI table.
    
    Args:
        db: Database session
        start_date: Optional date to filter rentals on or after (datetime.datetime)
        end_date: Optional date to filter rentals on or before (datetime.datetime)
    """
    # Subquery to calculate total seconds for completed rentals per user_id
    query = db.query(
        Rental.user_id,
        func.sum(
            (func.julianday(Rental.rental_end) - func.julianday(Rental.rental_start)) * 86400
        ).label("total_seconds"),
        func.count(Rental.id_re).label("rental_count")
    ).filter(Rental.rental_end != None)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Rental.rental_start >= start_date)
    if end_date:
        query = query.filter(Rental.rental_end <= end_date)
    
    # Complete the query
    subquery = query.group_by(Rental.user_id).subquery()

    # Main query joining User, Department, and the subquery
    results = db.query(
        User.name,
        Department.name.label("department_name"),
        subquery.c.total_seconds,
        subquery.c.rental_count
    ).select_from(User)\
    .join(Department, User.id_dep == Department.id_dep)\
    .filter(User.status == True)\
    .outerjoin(subquery, User.id_us == subquery.c.user_id)\
    .filter(subquery.c.total_seconds > 0)\
    .order_by(User.name)\
    .all()

    # Format results
    statistics = []
    
    for user_name, department_name, total_seconds, rental_count in results:
        # Преобразуем секунды в удобочитаемый формат
        if total_seconds:  # Проверяем, что total_seconds не None
            
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
            duration_parts = f"{int(days)}:{int(hours):02}:{int(minutes):02}"
            duration_str = duration_parts
            # days, remainder = divmod(total_seconds, 86400)
            # hours, remainder = divmod(remainder, 3600)
            # minutes, seconds = divmod(remainder, 60)
            
            # duration_parts = []
            # if days > 0: duration_parts.append(f"{int(days)}d")
            # if hours > 0: duration_parts.append(f"{int(hours)}h")
            # if minutes > 0: duration_parts.append(f"{int(minutes)}m")
            # if seconds > 0 or not duration_parts: duration_parts.append(f"{int(seconds)}s")
            
            # duration_str = " ".join(duration_parts)
        else:
            duration_str = "never rented"
            rental_count = 0
        
        statistics.append({
            "name": user_name,
            "department": department_name,
            "rental_count": rental_count,
            "total_rental_time": duration_str
        })
    
    return statistics

def get_equipment_type_statistics(db: Session, start_date=None, end_date=None) -> List[Dict]:
    """
    Get statistics for each equipment type including:
    - Total number of equipment of this type
    - Number of currently rented equipment
    - Total rental time across all equipment of this type
    Returns data in format suitable for GUI table.
    
    Args:
        db: Database session
        start_date: Optional date to filter rentals on or after (datetime.datetime)
        end_date: Optional date to filter rentals on or before (datetime.datetime)
    """
    # Get all equipment types
    etypes = get_all_etypes(db)
    
    # Get all equipment
    all_equipment = get_all_equipment(db)
    
    # Get active rentals
    active_rentals = get_active_rentals(db)
    
    # Dictionary to store statistics by equipment type ID
    stats_by_type = {}
    
    # Initialize stats for each type
    for etype in etypes:
        stats_by_type[etype.id_et] = {
            "type_name": etype.name,
            "total_equipment": 0,
            "rented_equipment": 0,
            "total_rental_seconds": 0,
            "rental_count": 0
        }
    
    # Count total equipment by type
    for equipment in all_equipment:
        if equipment.etype_id in stats_by_type:
            stats_by_type[equipment.etype_id]["total_equipment"] += 1
    
    # Count rented equipment by type
    for rental in active_rentals:
        if rental.equipment.etype_id in stats_by_type:
            stats_by_type[rental.equipment.etype_id]["rented_equipment"] += 1
    
    # Calculate total rental time for each type from completed rentals
    query = db.query(Rental).filter(Rental.rental_end != None)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Rental.rental_start >= start_date)
    if end_date:
        query = query.filter(Rental.rental_end <= end_date)
    
    completed_rentals = query.options(
        joinedload(Rental.equipment).joinedload(Equipment.etype)
    ).all()
    
    for rental in completed_rentals:
        etype_id = rental.equipment.etype_id
        if etype_id in stats_by_type:
            # Calculate rental duration in seconds
            start_time = rental.rental_start
            end_time = rental.rental_end
            duration = (end_time - start_time).total_seconds()
            stats_by_type[etype_id]["total_rental_seconds"] += duration
            stats_by_type[etype_id]["rental_count"] += 1
    
    # Format the results
    result = []
    for etype_id, stats in stats_by_type.items():
        # Convert seconds to human-readable format
        total_seconds = stats["total_rental_seconds"]
        
        # Skip types with zero rental time
        if total_seconds == 0:
            continue
            
        # Convert seconds to fractional days
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60
        duration_str = f"{int(days)}:{int(hours):02}:{int(minutes):02}"

        # days, remainder = divmod(total_seconds, 86400)
        # hours, remainder = divmod(remainder, 3600)
        # minutes, seconds = divmod(remainder, 60)
        
        # duration_parts = []
        # if days > 0: duration_parts.append(f"{int(days)}d")
        # if hours > 0: duration_parts.append(f"{int(hours)}h")
        # if minutes > 0: duration_parts.append(f"{int(minutes)}m")
        # if seconds > 0 or not duration_parts: duration_parts.append(f"{int(seconds)}s")
        
        # duration_str = " ".join(duration_parts)
        
        # Calculate availability percentage
        total = stats["total_equipment"]
        available = total - stats["rented_equipment"]
        availability_pct = (available / total * 100) if total > 0 else 100
        
        result.append({
            "type_name": stats["type_name"],
            "total_equipment": stats["total_equipment"],
            "available_equipment": available,
            "rented_equipment": stats["rented_equipment"],
            "availability_percentage": f"{availability_pct:.1f}%",
            "rental_count": stats["rental_count"],
            "total_rental_time": duration_str
        })
    
    # Sort by type name
    result.sort(key=lambda x: x["type_name"])
    
    return result

def get_all_departments_including_inactive(db: Session) -> List[Department]:
    """Get all departments including inactive ones"""
    return db.query(Department).all()

def get_all_equipment_including_inactive(db: Session) -> List[Equipment]:
    """Get all equipment including inactive ones"""
    return db.query(Equipment).options(joinedload(Equipment.etype)).all()

def get_all_etypes_including_inactive(db: Session) -> List[Etype]:
    """Get all equipment types including inactive ones"""
    return db.query(Etype).all()

def get_equipment_name_statistics(db: Session, start_date=None, end_date=None) -> List[Dict]:
    """
    Get statistics for each equipment name, grouping equipment with the same name.
    Calculates total rental time for all equipment with the same name.
    Returns data in format suitable for GUI table.
    
    Args:
        db: Database session
        start_date: Optional date to filter rentals on or after (datetime.datetime)
        end_date: Optional date to filter rentals on or before (datetime.datetime)
    """
    # Subquery to calculate total seconds for completed rentals per equipment_id
    query = db.query(
        Rental.equipment_id,
        func.sum(
            (func.julianday(Rental.rental_end) - func.julianday(Rental.rental_start)) * 86400
        ).label("total_seconds"),
        func.count(Rental.id_re).label("rental_count")
    ).filter(Rental.rental_end != None)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Rental.rental_start >= start_date)
    if end_date:
        query = query.filter(Rental.rental_end <= end_date)
    
    # Complete the query
    subquery = query.group_by(Rental.equipment_id).subquery()

    # Main query joining Equipment, Etype, and the subquery
    results = db.query(
        Equipment.name,
        Etype.name.label("etype_name"),
        func.count(Equipment.id_eq).label("equipment_count"),
        func.sum(subquery.c.total_seconds).label("total_seconds"),
        func.sum(subquery.c.rental_count).label("rental_count")
    ).select_from(Equipment)\
    .join(Etype, Equipment.etype_id == Etype.id_et)\
    .filter(Equipment.status == True)\
    .outerjoin(subquery, Equipment.id_eq == subquery.c.equipment_id)\
    .group_by(Equipment.name, Etype.name)\
    .having(func.sum(subquery.c.total_seconds) > 0)\
    .order_by(Equipment.name)\
    .all()

    # Format results
    statistics = []
    
    for name, etype_name, equipment_count, total_seconds, rental_count in results:
        # Преобразуем секунды в удобочитаемый формат
        if total_seconds:  # Проверяем, что total_seconds не None
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
            duration_parts = f"{int(days)}:{int(hours):02}:{int(minutes):02}"
            duration_str = duration_parts
        else:
            duration_str = "never rented"
            rental_count = 0
        
        statistics.append({
            "name": name,
            "etype_name": etype_name,
            "equipment_count": equipment_count,
            "rental_count": rental_count,
            "total_rental_time": duration_str
        })
    
    return statistics

def get_department_rental_statistics(db: Session, start_date=None, end_date=None) -> List[Dict]:
    """
    Get statistics for each department including:
    - Total number of rentals by department
    - Total rental time across all users in department
    Returns data in format suitable for GUI table.
    
    Args:
        db: Database session
        start_date: Optional date to filter rentals on or after (datetime.datetime)
        end_date: Optional date to filter rentals on or before (datetime.datetime)
    """
    # Subquery to calculate total seconds for completed rentals per department
    query = db.query(
        User.id_dep,
        func.sum(
            (func.julianday(Rental.rental_end) - func.julianday(Rental.rental_start)) * 86400
        ).label("total_seconds"),
        func.count(Rental.id_re).label("rental_count")
    ).join(User, Rental.user_id == User.id_us)\
    .filter(Rental.rental_end != None)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Rental.rental_start >= start_date)
    if end_date:
        query = query.filter(Rental.rental_end <= end_date)
    
    # Complete the query
    subquery = query.group_by(User.id_dep).subquery()

    # Main query joining Department and the subquery
    results = db.query(
        Department.name,
        subquery.c.rental_count,
        subquery.c.total_seconds
    ).select_from(Department)\
    .outerjoin(subquery, Department.id_dep == subquery.c.id_dep)\
    .filter(Department.status == True)\
    .order_by(Department.name)\
    .all()

    # Format results
    statistics = []
    
    for dept_name, rental_count, total_seconds in results:
        # Convert seconds to human-readable format
        if total_seconds:
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
            duration_str = f"{int(days)}:{int(hours):02}:{int(minutes):02}"
        else:
            duration_str = "never rented"
            rental_count = 0
        
        statistics.append({
            "name": dept_name,
            "rental_count": rental_count,
            "total_rental_time": duration_str
        })
    
    return statistics
