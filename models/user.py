# models/user.py
from sqlalchemy import Column, Integer, String, Boolean
from core.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    profile_image = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="customer")
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User {self.email}>"
