from sqlalchemy import Column, Integer, String
from core.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="customer")  # admin or customer

    def __repr__(self):
        return f"<User {self.full_name} ({self.email})>"
