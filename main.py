from nicegui import ui
from database import engine, SessionLocal
from crud import get_all_equipment, get_all_users, get_active_rentals
from gui import create_layout

def init_application():
    """Initialize the application"""
    # Database is already initialized in database.py
    pass

def main():
    """Main application entry point"""
    # Initialize application
    init_application()
    
    # Create GUI layout
    create_layout()
    
    # Start NiceGUI server
    ui.run(title="Equipment Rental System", port=8080)

if __name__ == "__main__":
    main()
