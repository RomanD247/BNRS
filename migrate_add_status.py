from sqlalchemy import create_engine, text
from models import Base
import os

# Use existing rental.db database
DATABASE_URL = "sqlite:///./rental.db"

def migrate():
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Add status columns to tables
    with engine.connect() as connection:
        try:
            # Add status column to equipment table
            connection.execute(text("""
                ALTER TABLE equipment 
                ADD COLUMN status BOOLEAN DEFAULT TRUE
            """))
            
            # Add status column to etypes table
            connection.execute(text("""
                ALTER TABLE etypes 
                ADD COLUMN status BOOLEAN DEFAULT TRUE
            """))
            
            # Add status column to departments table
            connection.execute(text("""
                ALTER TABLE departments 
                ADD COLUMN status BOOLEAN DEFAULT TRUE
            """))
            
            # Add status column to users table
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN status BOOLEAN DEFAULT TRUE
            """))
            
            connection.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            connection.rollback()

if __name__ == "__main__":
    migrate()