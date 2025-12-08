from core.db import Base, engine, SessionLocal
from models.user import User
from models.food_item import FoodItem
from models.order import Order, OrderItem
from models.cart import Cart
from models.audit_log import AuditLog
from models.login_attempt import LoginAttempt
from core.user_service import create_default_admin

def seed_food_items(db):
    existing = db.query(FoodItem).first()
    if not existing:
        sample_items = [
            FoodItem(name="BimBimBowl", description="Rice, Egg, Carrot, Cucumber, Kangkong, Pork, Corn Etc.", category="Korean Bowls", price=100.0, image="assets/uploads/foods/bimbimbowl.jpg"),
            FoodItem(name="Buldak Spicy Chicken", description="Korean fire chicken.", category="Noodles", price=90.0, image="assets/uploads/foods/hotspicy.jpg"),
            FoodItem(name="Spam Bowl", description="Rice, Spam, Egg, Veggies, Corn Etc.", category="Korean Bowls", price=100.0, image="assets/uploads/foods/spambowl.jpg"),
            FoodItem(name="Kimchi Fried Rice", description="Spicy kimchi rice.", category="Korean Bowls", price=180.0, image="assets/kimchi_rice.png"),
            FoodItem(name="Ramen + Chicken Combo", description="Best combo meal.", category="Combo", price=400.0, image="assets/combo1.png"),
            FoodItem(name="Extra Egg", description="Soft boiled egg topping.", category="Toppings", price=30.0, image="assets/egg.png"),
            FoodItem(name="Iced Milk Tea", description="Refreshing milk tea.", category="Drinks", price=120.0, image="assets/drink1.png"),
            FoodItem(name="Korean Soda", description="Sparkling Korean drink.", category="Drinks", price=80.0, image="assets/soda.png"),
        ]
        db.add_all(sample_items)
        db.commit()
        print("Sample food items seeded.")
    else:
        print("Food items already seeded.")

def init_db():
    print("Rebuilding database (drop/create)...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("All tables created:")
    print("   - users")
    print("   - food_items")
    print("   - orders")
    print("   - order_items")
    print("   - carts")
    print("   - audit_logs")
    print("   - login_attempts") 
    
    db = SessionLocal()
    
    # Create default admin
    create_default_admin(db)
    
    # Seed food items
    seed_food_items(db)
    
    db.close()
    print("\nDatabase initialization complete!")
    print("Default admin: admin@pojangmacha.com / admin123")

if __name__ == "__main__":
    init_db()