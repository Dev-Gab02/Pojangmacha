# core/session_manager.py
import time, os
from dotenv import load_dotenv

load_dotenv()

SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "60"))  # seconds for demo
_sessions = {}

def start_session(email: str):
    _sessions[email] = time.time()

def refresh_session(email: str):
    """Update last active time on user interaction."""
    if email in _sessions:
        _sessions[email] = time.time()

def is_session_active(email: str, return_remaining=False):
    """Check if session still active; optionally return remaining seconds."""
    last = _sessions.get(email)
    if not last:
        return (False, 0) if return_remaining else False
    elapsed = time.time() - last
    remaining = max(0, SESSION_TIMEOUT - elapsed)
    if elapsed > SESSION_TIMEOUT:
        _sessions.pop(email, None)
        return (False, 0) if return_remaining else False
    if return_remaining:
        return (True, remaining)
    return True

def end_session(email: str):
    _sessions.pop(email, None)
