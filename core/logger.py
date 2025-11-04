# core/logger.py
from core.db import SessionLocal
from models.audit_log import AuditLog
from datetime import datetime

def log_action(user_email: str, action: str):
    """Add a new log entry."""
    db = SessionLocal()
    try:
        entry = AuditLog(user_email=user_email, action=action, timestamp=datetime.utcnow())
        db.add(entry)
        db.commit()
    except Exception as e:
        print("⚠️ Logger error:", e)
        db.rollback()
    finally:
        db.close()
