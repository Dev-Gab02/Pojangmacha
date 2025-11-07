# core/auth_service.py
import bcrypt
import secrets
import time
from sqlalchemy.orm import Session
from models.user import User
from models.audit_log import AuditLog

# --- In-memory attempt tracking ---
_failed_attempts = {}

LOCKOUT_THRESHOLD = 3        # Number of attempts before lock
LOCKOUT_TIME = 60            # 60 seconds lock

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_user(db: Session, full_name, email, phone, password, role="customer"):
    if db.query(User).filter(User.email == email).first():
        return None
    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user with throttling and logging"""
    now = time.time()
    info = _failed_attempts.get(email)

    # Lockout check
    if info and info["count"] >= LOCKOUT_THRESHOLD and now - info["last"] < LOCKOUT_TIME:
        remaining = int(LOCKOUT_TIME - (now - info["last"]))
        return None, f"Account locked. Try again in {remaining}s."

    user = db.query(User).filter(User.email == email).first()

    # Verify credentials
    if not user or not verify_password(password, user.password_hash):
        _failed_attempts[email] = {
            "count": (info["count"] + 1 if info else 1),
            "last": now
        }
        remaining = LOCKOUT_THRESHOLD - _failed_attempts[email]["count"]
        remaining = max(0, remaining)
        db.add(AuditLog(user_email=email, action="Failed login attempt"))
        db.commit()

        if remaining == 0:
            return None, "Too many failed attempts. Account temporarily locked."
        return None, f"Invalid credentials. {remaining} attempts left."

    # Success
    _failed_attempts.pop(email, None)
    db.add(AuditLog(user_email=email, action="Successful login"))
    db.commit()
    return user, "Login successful."
