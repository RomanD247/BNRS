# Equipment Rental Application Development Plan

## 1. Project Description
An application for managing equipment rentals in an internal warehouse. Users will be able to rent and return equipment, view rental history, and generate reports.

## 2. Technologies
- **Language:** Python
- **Database:** SQLite
- **ORM:** SQLAlchemy
- **GUI:** NiceGUI (accessible via browser)
- **Environment:** Local network

---

## 3. Main Components

### 3.1 Database
- **Equipment:** `id_us`, `name`, `serialnum`, `etype`
- **Departments** `id_et`, `name`,
- **Users:** `id_eq`, `name`, `dep`
- **Rentals:** `id_re`, `equipment_id`, `user_id`, `rental_start`, `rental_end`

### 3.2 Functionality
- Add new equipment and users
- Rent and return equipment
- View available and rented equipment
- View rental history
- Generate reports (e.g., total rental time, list of equipment rented by a specific user, etc.)

---

## 4. Project Structure
```
project_name/
│
├── main.py                  # Entry point
├── models.py               # SQLAlchemy models
├── database.py             # Database initialization
├── crud.py                 # CRUD operations
├── gui.py                  # Interface using NiceGUI
├── utils.py                # Utility functions
├── reports.py              # Report generation
└── static/                 # Static files (if needed)
```

---

## 5. Development Plan

### Stage 1: Project Initialization
- Set up a virtual environment
- Install dependencies (`SQLAlchemy`, `SQLite`, `NiceGUI`)

### Stage 2: Database Creation
- Develop models and relationships in `models.py`
- Implement database initialization functions in `database.py`

### Stage 3: Application Logic
- Implement CRUD operations in `crud.py`
- Implement rental and return functions

### Stage 4: User Interface
- Create a basic structure with NiceGUI
- Add pages to view equipment, rent, and return it

### Stage 5: Reports and Analytics
- Implement reports in `reports.py`
- Add filtering and sorting options

### Stage 6: Testing and Debugging
- Add test data
- Test all functions

