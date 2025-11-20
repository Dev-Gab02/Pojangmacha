from datetime import datetime, timedelta
import threading

# In-memory session storage (email -> last activity timestamp)
active_sessions = {}
session_lock = threading.Lock()

# Session timeout in seconds (from .env or default 180 = 3 minutes)
import os
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "180"))

def start_session(email: str):
    """Start a new session for the user"""
    with session_lock:
        active_sessions[email] = datetime.utcnow()
        print(f"✅ Session started for {email}")

def end_session(email: str):
    """End the session for the user"""
    with session_lock:
        if email in active_sessions:
            del active_sessions[email]
            print(f"🔴 Session ended for {email}")

def refresh_session(email: str):
    """Refresh (update) the last activity timestamp"""
    with session_lock:
        if email in active_sessions:
            old_timestamp = active_sessions[email]
            active_sessions[email] = datetime.utcnow()
            elapsed = (datetime.utcnow() - old_timestamp).total_seconds()
            print(f"🔄 Session refreshed for {email} (was idle for {elapsed:.1f}s)")
            return True
        else:
            print(f"⚠️ Cannot refresh - no active session for {email}")
            return False

def is_session_active(email: str, return_remaining: bool = False):
    """
    Check if a session is still active.
    
    Args:
        email: User email
        return_remaining: If True, returns (active, remaining_seconds)
    
    Returns:
        bool or tuple: Session status, optionally with remaining time
    """
    with session_lock:
        if email not in active_sessions:
            return (False, 0) if return_remaining else False
        
        last_activity = active_sessions[email]
        elapsed = (datetime.utcnow() - last_activity).total_seconds()
        remaining = SESSION_TIMEOUT - elapsed
        
        is_active = remaining > 0
        
        if return_remaining:
            return (is_active, max(0, remaining))
        return is_active

def get_all_active_sessions():
    """Get all active sessions (for debugging)"""
    with session_lock:
        return {email: timestamp for email, timestamp in active_sessions.items()}

def check_any_active_lockout(db):
    """Check if there's ANY active lockout in the system"""
    from models.login_attempt import LoginAttempt
    
    # Get all locked accounts
    locked_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.locked_until.isnot(None)
    ).all()
    
    for attempt in locked_attempts:
        if datetime.utcnow() < attempt.locked_until:
            remaining = int((attempt.locked_until - datetime.utcnow()).total_seconds())
            return True, attempt.email, attempt.locked_until, remaining
    
    return False, None, None, 0