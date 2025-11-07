# models/password_reset.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timedelta
from core.db import Base

class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_expiry(minutes: int = 10):
        return datetime.utcnow() + timedelta(minutes=minutes)
