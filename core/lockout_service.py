import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from core.db import SessionLocal
from models.login_attempt import LoginAttempt

load_dotenv()
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "2"))

def get_global_failed_attempts(db):
    """
    Count failed login attempts (any email) in the last LOCKOUT_DURATION_MINUTES.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    return db.query(LoginAttempt).filter(
        LoginAttempt.success == False,
        LoginAttempt.attempt_time >= cutoff,
        LoginAttempt.email != "__GLOBAL_LOCKOUT__"
    ).count()

def set_global_lockout(db):
    """
    Set a global lockout by creating a special record.
    """
    locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    db.add(LoginAttempt(
        email="__GLOBAL_LOCKOUT__",
        success=False,
        attempt_time=datetime.utcnow(),
        locked_until=locked_until,
        failed_attempts=MAX_FAILED_ATTEMPTS
    ))
    db.commit()

def get_global_lockout(db):
    """
    Get the current global lockout expiration datetime, or None if not locked.
    """
    now = datetime.utcnow()
    lockout = db.query(LoginAttempt).filter(
        LoginAttempt.email == "__GLOBAL_LOCKOUT__",
        LoginAttempt.locked_until != None,
        LoginAttempt.locked_until > now
    ).order_by(LoginAttempt.locked_until.desc()).first()
    if lockout:
        return lockout.locked_until
    return None

def clear_global_lockout(db):
    """
    Remove all global lockout records.
    """
    db.query(LoginAttempt).filter(LoginAttempt.email == "__GLOBAL_LOCKOUT__").delete()
    db.commit()

def record_login_attempt(db, email, success):
    """
    Record a login attempt for any email.
    """
    attempt = LoginAttempt(
        email=email,
        success=success,
        attempt_time=datetime.utcnow(),
        failed_attempts=0
    )
    db.add(attempt)
    db.commit()