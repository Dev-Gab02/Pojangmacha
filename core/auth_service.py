# core/auth_service.py
import bcrypt, time
from sqlalchemy.orm import Session
from models.user import User
from datetime import datetime, timedelta
import secrets

# in-memory stores for demo
_failed_attempts = {}
_reset_tokens = {}

LOCKOUT_THRESHOLD = 3        # attempts
LOCKOUT_TIME = 60            # seconds
RESET_TOKEN_EXPIRY = 600     # 10 minutes

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
    
def create_user_from_google(db: Session, email: str, full_name: str, picture: str = None):
    """
    Create or get user from Google OAuth
    If user exists, return it. If not, create new user.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"User {email} already exists - logging in")
        return existing_user
    
    # Create new user with random password (they'll use Google login)
    random_password = secrets.token_urlsafe(32)
    hashed_pwd = hash_password(random_password)
    
    new_user = User(
        email=email,
        password_hash=hashed_pwd,
        full_name=full_name,
        phone="",  # Optional for Google users
        role="customer",
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"Created new Google user: {email}")
    return new_user

def create_user(db: Session, full_name, email, phone, password, role="customer"):
    if db.query(User).filter(User.email == email).first():
        return None
    user = User(full_name=full_name, email=email, phone=phone,
                password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email, password):
    """Return (user, message). message is helpful for UI."""
    now = time.time()
    info = _failed_attempts.get(email)
    if info and info["count"] >= LOCKOUT_THRESHOLD and now - info["last"] < LOCKOUT_TIME:
        wait = LOCKOUT_TIME - int(now - info["last"])
        return None, f"Account locked. Try again in {wait}s."

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        _failed_attempts[email] = {"count": (info["count"] + 1 if info else 1), "last": now}
        remaining = max(0, LOCKOUT_THRESHOLD - _failed_attempts[email]["count"])
        if remaining == 0:
            return None, "Account locked due to too many failed attempts."
        return None, f"Invalid credentials. {remaining} attempts left."
    # success
    _failed_attempts.pop(email, None)
    user.failed_attempts = 0
    user.is_locked = 0
    user.last_login = None
    db.add(user)
    db.commit()
    return user, "Login successful."

def generate_reset_token(email: str):
    token = secrets.token_hex(4)
    _reset_tokens[email] = {"token": token, "time": time.time()}
    # token would normally be emailed; print to console for demo
    print(f"[PASSWORD RESET] Token for {email}: {token}")
    return token

def verify_reset_token(db: Session, email: str, token: str, new_password: str):
    record = _reset_tokens.get(email)
    if not record:
        return False
    if record["token"] != token:
        return False
    if time.time() - record["time"] > RESET_TOKEN_EXPIRY:
        _reset_tokens.pop(email, None)
        return False
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    _reset_tokens.pop(email, None)
    return True
