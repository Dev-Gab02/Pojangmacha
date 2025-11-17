from sqlalchemy.orm import Session
from models.cart import Cart
from models.food_item import FoodItem

def get_user_cart(db: Session, user_id: int):
    """Get all cart items for a user"""
    return db.query(Cart).filter(Cart.user_id == user_id).all()

def add_to_cart(db: Session, user_id: int, food_id: int, quantity: int = 1):
    """Add item to cart or update quantity if exists"""
    # Check if item already in cart
    cart_item = db.query(Cart).filter(
        Cart.user_id == user_id,
        Cart.food_id == food_id
    ).first()
    
    if cart_item:
        # Update quantity
        cart_item.quantity += quantity
    else:
        # Add new item
        cart_item = Cart(
            user_id=user_id,
            food_id=food_id,
            quantity=quantity
        )
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart_item)
    return cart_item

def update_cart_quantity(db: Session, cart_id: int, quantity: int):
    """Update cart item quantity"""
    cart_item = db.query(Cart).filter(Cart.id == cart_id).first()
    if cart_item:
        if quantity <= 0:
            db.delete(cart_item)
        else:
            cart_item.quantity = quantity
        db.commit()
        return True
    return False

def remove_from_cart(db: Session, cart_id: int):
    """Remove item from cart"""
    cart_item = db.query(Cart).filter(Cart.id == cart_id).first()
    if cart_item:
        db.delete(cart_item)
        db.commit()
        return True
    return False

def clear_user_cart(db: Session, user_id: int):
    """Clear all cart items for a user"""
    db.query(Cart).filter(Cart.user_id == user_id).delete()
    db.commit()

def get_cart_count(db: Session, user_id: int):
    """Get total number of items in cart"""
    items = db.query(Cart).filter(Cart.user_id == user_id).all()
    return sum(item.quantity for item in items)