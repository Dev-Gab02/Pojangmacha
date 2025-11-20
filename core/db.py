# core/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pojangmacha.db")

# Use future flag and disable check_same_thread only for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create engine (fu ture mode)
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)

# SessionLocal factory: expire_on_commit=False avoids needing refresh() in many places
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)

Base = declarative_base()


def get_db():
    """Yield a SQLAlchemy session (use: `with get_db() as db:` or `for db in get_db():`)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
