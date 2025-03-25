from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# SQLite database URL (можно заменить на другую БД при необходимости)
DATABASE_URL = "sqlite:///rental.db"

# Создание движка БД
engine = create_engine(DATABASE_URL, echo=True)

# Создание фабрики сессий
SessionLocal = sessionmaker(bind=engine)

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)
