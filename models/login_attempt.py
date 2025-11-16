from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from core.db import Base

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    ip_address = Column(String, nullable=True)
    success = Column(Boolean, default=False)
    attempt_time = Column(DateTime, default=datetime.utcnow)
    locked_until = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)