# core/profile_service.py
from sqlalchemy.orm import Session
from models.user import User
from models.audit_log import AuditLog
from core.auth_service import hash_password, verify_password
from datetime import datetime


def get_user_by_id(db: Session, user_id: int):
    """Fetch user record by ID."""
    return db.query(User).filter(User.id == user_id).first()


def update_profile(db: Session, user_id: int, full_name: str, email: str, phone: str, profile_picture: str = None):
    """Update basic profile info."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User not found."

    # Prevent duplicate email usage
    existing = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing:
        return False, "Email already in use by another account."

    user.full_name = full_name
    user.email = email
    user.phone = phone
    if profile_picture:
        user.profile_picture = profile_picture

    db.commit()
    db.add(AuditLog(user_email=user.email, action=f"Updated profile info at {datetime.utcnow()}"))
    db.commit()
    return True, "Profile updated successfully."


def change_password(db: Session, user_id: int, old_password: str, new_password: str):
    """Change password after verifying the old one."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User not found."

    if not verify_password(old_password, user.password_hash):
        return False, "Incorrect current password."

    user.password_hash = hash_password(new_password)
    db.commit()
    db.add(AuditLog(user_email=user.email, action=f"Changed password at {datetime.utcnow()}"))
    db.commit()
    return True, "Password changed successfully."