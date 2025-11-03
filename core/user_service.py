# core/user_service.py
from sqlalchemy.orm import Session
from models.user import User
from core.auth_service import hash_password

def create_default_admin(db: Session):
    admin_email = "admin@gmail.com"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin = User(
            full_name="Admin User",
            email=admin_email,
            phone="0000000000",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
        print("✅ Default admin created: admin@gmail.com / admin123")
    else:
        print("Admin already exists.")
