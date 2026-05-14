from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), default="")
    role = Column(String(50), default="customer")
    two_fa_enabled = Column(Boolean, default=False)
    two_fa_backup_codes = Column(String(255), nullable=True)
    google_id = Column(String(255), nullable=True)
    profile_picture = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    cart_items = relationship("Cart", back_populates="user", cascade="all, delete-orphan")