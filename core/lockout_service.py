from sqlalchemy.orm import Session
from models.login_attempt import LoginAttempt
from datetime import datetime, timedelta
import os

# Configuration
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "3"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

def record_failed_attempt(db: Session, email: str, ip_address: str = None):
    """Record a failed login attempt and check if account should be locked"""
    
    # Get or create login attempt record
    attempt = db.query(LoginAttempt).filter(LoginAttempt.email == email).first()
    
    if not attempt:
        attempt = LoginAttempt(
            email=email,
            ip_address=ip_address,
            failed_attempts=1,
            attempt_time=datetime.utcnow()
        )
        db.add(attempt)
    else:
        # Check if previous lockout expired
        if attempt.locked_until and datetime.utcnow() < attempt.locked_until:
            # Still locked - don't increment
            db.commit()
            return attempt.failed_attempts, attempt.locked_until
        
        # Lockout expired or never locked - reset if more than 15 minutes passed
        if (datetime.utcnow() - attempt.attempt_time).total_seconds() > 900:  # 15 minutes
            attempt.failed_attempts = 1
        else:
            attempt.failed_attempts += 1
        
        attempt.attempt_time = datetime.utcnow()
        attempt.ip_address = ip_address
    
    # Lock account if max attempts reached
    if attempt.failed_attempts >= MAX_FAILED_ATTEMPTS:
        attempt.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    
    db.commit()
    db.refresh(attempt)
    
    return attempt.failed_attempts, attempt.locked_until

def record_successful_login(db: Session, email: str):
    """Reset failed attempts on successful login"""
    attempt = db.query(LoginAttempt).filter(LoginAttempt.email == email).first()
    
    if attempt:
        attempt.failed_attempts = 0
        attempt.locked_until = None
        attempt.success = True
        attempt.attempt_time = datetime.utcnow()
        db.commit()

def is_account_locked(db: Session, email: str):
    """Check if account is currently locked"""
    attempt = db.query(LoginAttempt).filter(LoginAttempt.email == email).first()
    
    if not attempt:
        return False, None, 0
    
    # Check if locked and lockout still active
    if attempt.locked_until and datetime.utcnow() < attempt.locked_until:
        remaining_seconds = int((attempt.locked_until - datetime.utcnow()).total_seconds())
        return True, attempt.locked_until, remaining_seconds
    
    # Lockout expired - clear it
    if attempt.locked_until:
        attempt.locked_until = None
        attempt.failed_attempts = 0
        db.commit()
    
    return False, None, 0

def get_remaining_attempts(db: Session, email: str):
    """Get number of remaining login attempts"""
    attempt = db.query(LoginAttempt).filter(LoginAttempt.email == email).first()
    
    if not attempt:
        return MAX_FAILED_ATTEMPTS
    
    # If locked, return 0
    if attempt.locked_until and datetime.utcnow() < attempt.locked_until:
        return 0
    
    remaining = MAX_FAILED_ATTEMPTS - attempt.failed_attempts
    return max(0, remaining)

def format_lockout_time(seconds: int):
    """Format remaining lockout time as MM:SS"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"

def check_any_active_lockout(db: Session):
    """Check if there's ANY active lockout in the system (NEW)"""
    # Get all locked accounts
    locked_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.locked_until.isnot(None)
    ).all()
    
    for attempt in locked_attempts:
        if datetime.utcnow() < attempt.locked_until:
            remaining = int((attempt.locked_until - datetime.utcnow()).total_seconds())
            return True, attempt.email, attempt.locked_until, remaining
    
    return False, None, None, 0