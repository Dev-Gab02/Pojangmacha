# core/logger.py
from core.db import SessionLocal
from models.audit_log import AuditLog
from datetime import datetime

def log_action(user_email: str, action: str):
    """Record an admin or user action into the audit log."""
    session = SessionLocal()
    try:
        log = AuditLog(user_email=user_email, action=action, timestamp=datetime.utcnow())
        session.add(log)
        session.commit()
    except Exception as e:
        print("Audit log error:", e)
        session.rollback()
    finally:
        session.close()
