# core/session_manager.py
import time
import os
from dotenv import load_dotenv

# Load environment variables (SESSION_TIMEOUT in seconds)
load_dotenv()
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "120"))  # default 5 min

_sessions = {}

def start_session(user_email: str):
    _sessions[user_email] = {"last": time.time()}

def refresh_session(user_email: str):
    """Extend session on user activity."""
    if user_email in _sessions:
        _sessions[user_email]["last"] = time.time()

def is_session_active(user_email: str):
    """Return (active, remaining_seconds)."""
    session = _sessions.get(user_email)
    if not session:
        return False, 0
    elapsed = time.time() - session["last"]
    remaining = SESSION_TIMEOUT - elapsed
    if remaining <= 0:
        _sessions.pop(user_email, None)
        return False, 0
    return True, int(remaining)

def end_session(user_email: str):
    _sessions.pop(user_email, None)
