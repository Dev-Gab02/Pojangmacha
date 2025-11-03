# init_db.py
from core.db import Base, engine, SessionLocal
from models.user import User
from models.food_item import FoodItem
from models.order import Order, OrderItem
from models.audit_log import AuditLog
from core.user_service import create_default_admin

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

    db = SessionLocal()
    create_default_admin(db)
    db.close()

if __name__ == "__main__":
    init_db()
