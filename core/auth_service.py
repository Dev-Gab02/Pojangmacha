# core/auth_service.py
# Authentication helpers: bcrypt hashing, verify, create_user, authenticate_user
import bcrypt
import time
from sqlalchemy.orm import Session
from models.user import User

# Optional simple lockout storage (in-memory demo)
_failed_attempts = {}
LOCKOUT_THRESHOLD = 5
LOCKOUT_TIME = 60  # seconds

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_user(db: Session, full_name: str, email: str, phone: str, password: str, role: str = "customer"):
    """
    Create a new user. Returns (user, message).
    If email exists returns (None, "Email already exists").
    """
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None, "Email already exists."
    user = User(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        phone=(phone.strip() if phone else None),
        password_hash=hash_password(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, "Account created."

def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate user. Returns (user, message).
    Implements a simple lockout after repeated failures (in-memory demo).
    """
    now = time.time()
    key = email.strip().lower()
    info = _failed_attempts.get(key)
    if info and info["count"] >= LOCKOUT_THRESHOLD and now - info["last"] < LOCKOUT_TIME:
        wait = LOCKOUT_TIME - int(now - info["last"])
        return None, f"Account locked. Try again in {wait}s."

    user = db.query(User).filter(User.email == key).first()
    if not user:
        _failed_attempts[key] = {"count": (info["count"] + 1 if info else 1), "last": now}
        remaining = max(0, LOCKOUT_THRESHOLD - _failed_attempts[key]["count"])
        return None, f"Invalid credentials. {remaining} attempts left."

    if not verify_password(password, user.password_hash):
        _failed_attempts[key] = {"count": (info["count"] + 1 if info else 1), "last": now}
        remaining = max(0, LOCKOUT_THRESHOLD - _failed_attempts[key]["count"])
        if remaining == 0:
            return None, "Account locked due to too many failed attempts."
        return None, f"Invalid credentials. {remaining} attempts left."

    # success -> clear failures
    _failed_attempts.pop(key, None)
    return user, "Login successful."
