from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# SQLite database URL (can be replaced with another database if necessary)
DATABASE_URL = "sqlite:///rental.db"

# Creating a DB Engine
engine = create_engine(DATABASE_URL, echo=True)

# Creating a Session Factory
SessionLocal = sessionmaker(bind=engine)

# Creating tables in a database
Base.metadata.create_all(bind=engine)
