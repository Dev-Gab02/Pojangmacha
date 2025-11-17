# core/user_service.py
from sqlalchemy.orm import Session
from models.user import User
from core.auth_service import hash_password
from core.config import ADMIN_EMAIL, ADMIN_PASSWORD

def create_default_admin(db: Session):
    admin_email = ADMIN_EMAIL or "admin@gmail.com"
    admin_pass = ADMIN_PASSWORD or "admin123"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin = User(
            full_name="Admin User",
            email=admin_email,
            phone="0000000000",
            password_hash=hash_password(admin_pass),
            role="admin"
        )
        db.add(admin)
        db.commit()
        print(f"✅ Default admin created: {admin_email} / {admin_pass}")
    else:
        print("Admin already exists.")
