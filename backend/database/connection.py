import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Fetch database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to local SQLite during development if no Postgres URL is provided
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///recruiter.db"
elif DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy requires "postgresql://" instead of "postgres://"
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite requires different connection arguments than Postgres
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency to yield db session and close it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
