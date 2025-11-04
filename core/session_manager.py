# core/session_manager.py
import time
import os
from dotenv import load_dotenv

load_dotenv()

SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "900"))  # default 15 min
WARNING_TIME = int(os.getenv("SESSION_WARNING", "60"))      # warn 1 min before logout
_sessions = {}

def start_session(user_email: str):
    _sessions[user_email] = time.time()

def refresh_session(user_email: str):
    if user_email in _sessions:
        _sessions[user_email] = time.time()

def is_session_active(user_email: str):
    """
    Returns tuple (active: bool, remaining_seconds: int)
    """
    last = _sessions.get(user_email)
    if not last:
        return False, 0
    elapsed = time.time() - last
    remaining = SESSION_TIMEOUT - elapsed
    if remaining <= 0:
        _sessions.pop(user_email, None)
        return False, 0
    return True, int(remaining)

def end_session(user_email: str):
    _sessions.pop(user_email, None)
