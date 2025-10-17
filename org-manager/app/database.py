from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database configuration for multiple environments
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orgs.db")

# For Railway PostgreSQL (if provided)
if DATABASE_URL.startswith("postgresql://"):
    # Ensure we have psycopg2 for PostgreSQL
    pass
else:
    # SQLite for development/local
    pass

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
