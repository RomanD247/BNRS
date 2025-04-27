# Equipment Rental Application Development Plan - Updated

## 1. Project Description
An application for managing equipment rentals in an internal warehouse. Users can rent and return equipment, view rental history, and generate reports. The application includes NFC scanning capability for equipment and users.

## 2. Technologies
- **Language:** Python
- **Database:** SQLite
- **ORM:** SQLAlchemy
- **GUI:** NiceGUI (accessible via browser)
- **Environment:** Local network
- **Data Analysis:** Pandas
- **Configuration:** python-dotenv

---

## 3. Main Components

### 3.1 Database
- **Equipment:** `id_eq`, `name`, `serialnum`, `etype_id`, `status`, `nfc`
- **Equipment Types:** `id_et`, `name`, `status`
- **Departments:** `id_dep`, `name`, `status`
- **Users:** `id_us`, `name`, `id_dep`, `status`, `nfc`
- **Rentals:** `id_re`, `equipment_id`, `user_id`, `rental_start`, `rental_end`, `comment`
- **Feedback:** `id_fb`, `name`, `date`, `feedback`

### 3.2 Functionality
- Add, update, and delete equipment, equipment types, users, and departments
- Rent and return equipment with optional comments
- View available and rented equipment
- View rental history with filtering options
- Generate reports (e.g., rental history, equipment status, user activity)
- NFC scanning for quick identification of users and equipment
- User feedback system

---

## 4. Project Structure
```
equipment_rental/
│
├── main.py                  # Entry point and main application
├── models.py                # SQLAlchemy models
├── database.py              # Database initialization
├── crud.py                  # CRUD operations
├── NfcScan.py               # NFC scanning functionality
├── requirements.txt         # Project dependencies
├── rental.db                # SQLite database
│
├── gui/                     # GUI components
│   ├── __init__.py
│   ├── gui_addequip.py      # Equipment addition interface
│   ├── gui_adduser.py       # User addition interface
│   ├── gui_changeEquip.py   # Equipment management interface
│   ├── gui_changeDep.py     # Department management interface
│   ├── gui_changeEtype.py   # Equipment type management interface
│   ├── gui_changeUser.py    # User management interface
│   └── gui_reports.py       # Reports and analytics interface
│
└── assets/                  # Static files and resources
```

---

## 5. Development Status

### Completed
- Project initialization and dependency setup
- Database models and schema creation
- CRUD operations for all entities
- User interface implementation with NiceGUI
- Equipment rental and return functionality
- NFC scanning integration
- Basic reporting and analytics
- User feedback system

### In Progress
- Advanced filtering for reports
- User experience improvements
- Performance optimization