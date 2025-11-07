# core/auth_service.py
import bcrypt
import secrets
import time
from datetime import datetime
from sqlalchemy.orm import Session
from models.user import User
from models.audit_log import AuditLog
from models.password_reset import PasswordReset

# --- In-memory attempt tracking ---
_failed_attempts = {}

LOCKOUT_THRESHOLD = 3        # Number of attempts before lock
LOCKOUT_TIME = 60            # 60 seconds lock

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
    
def create_password_reset(db, email: str):
    """Create password reset token for user"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None, "Email not registered."

    token = secrets.token_urlsafe(16)
    reset_entry = PasswordReset(
        email=email,
        token=token,
        expires_at=PasswordReset.generate_expiry(10)
    )
    db.add(reset_entry)
    db.commit()
    db.add(AuditLog(user_email=email, action="Requested password reset"))
    db.commit()
    return token, "Password reset link generated (token logged)."

def verify_reset_token(db, token: str):
    """Verify if reset token is valid and not expired"""
    entry = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    if not entry:
        return None, "Invalid or expired token."
    if datetime.utcnow() > entry.expires_at:
        return None, "Token has expired."
    return entry.email, "Token verified."

def reset_password_with_token(db, token: str, new_password: str):
    """Reset password using valid token"""
    email, msg = verify_reset_token(db, token)
    if not email:
        return False, msg
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False, "User not found."
    
    # Update password
    user.password_hash = hash_password(new_password)
    db.commit()
    
    # Mark token as used by deleting it
    entry = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    if entry:
        db.delete(entry)
        db.commit()
    
    db.add(AuditLog(user_email=email, action="Password reset completed"))
    db.commit()
    
    return True, "Password reset successfully."

def create_user(db: Session, full_name, email, phone, password, role="customer"):
    """Create new user account - Returns tuple (user, message)"""
    # Check if user already exists
    if db.query(User).filter(User.email == email).first():
        return None, "Email already registered."
    
    # Create new user
    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log the registration
    db.add(AuditLog(user_email=email, action="User registered"))
    db.commit()
    
    return user, "Account created successfully."

def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user with throttling and logging - Returns tuple (user, message)"""
    now = time.time()
    info = _failed_attempts.get(email)

    # Lockout check
    if info and info["count"] >= LOCKOUT_THRESHOLD and now - info["last"] < LOCKOUT_TIME:
        remaining = int(LOCKOUT_TIME - (now - info["last"]))
        return None, f"Account locked. Try again in {remaining}s."

    user = db.query(User).filter(User.email == email).first()

    # Check if user exists and is active
    if not user:
        _failed_attempts[email] = {
            "count": (info["count"] + 1 if info else 1),
            "last": now
        }
        remaining = LOCKOUT_THRESHOLD - _failed_attempts[email]["count"]
        remaining = max(0, remaining)
        db.add(AuditLog(user_email=email, action="Failed login attempt - user not found"))
        db.commit()
        
        if remaining == 0:
            return None, "Too many failed attempts. Account temporarily locked."
        return None, f"Invalid credentials. {remaining} attempts left."
    
    if not user.is_active:
        db.add(AuditLog(user_email=email, action="Login attempt on inactive account"))
        db.commit()
        return None, "Account is disabled. Contact administrator."

    # Verify password
    if not verify_password(password, user.password_hash):
        _failed_attempts[email] = {
            "count": (info["count"] + 1 if info else 1),
            "last": now
        }
        remaining = LOCKOUT_THRESHOLD - _failed_attempts[email]["count"]
        remaining = max(0, remaining)
        db.add(AuditLog(user_email=email, action="Failed login attempt - wrong password"))
        db.commit()

        if remaining == 0:
            return None, "Too many failed attempts. Account temporarily locked."
        return None, f"Invalid credentials. {remaining} attempts left."

    # Success
    _failed_attempts.pop(email, None)
    db.add(AuditLog(user_email=email, action="Successful login"))
    db.commit()
    return user, "Login successful."