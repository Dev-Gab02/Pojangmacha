# core/session_manager.py
# Simple in-memory session tracker for demo
import time
import os
from dotenv import load_dotenv

load_dotenv()

# seconds default (can override with .env)
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "900"))  # 15 minutes default

_sessions = {}

def start_session(user_email: str):
    _sessions[user_email] = time.time()

def refresh_session(user_email: str):
    """Mark activity for user — extend their session expiry."""
    if user_email in _sessions:
        _sessions[user_email] = time.time()

def is_session_active(user_email: str) -> bool:
    """
    Check activity state without refreshing.
    Returns True if active, False otherwise. If expired, removes session.
    """
    last = _sessions.get(user_email)
    if not last:
        return False
    if time.time() - last > SESSION_TIMEOUT:
        _sessions.pop(user_email, None)
        return False
    return True

def end_session(user_email: str):
    _sessions.pop(user_email, None)
